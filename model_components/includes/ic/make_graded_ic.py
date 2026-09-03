"""Reusable graded initial-condition builder for CSIEM TUFLOW-FV.

Grades SAL and TEMP across the (uniform) base 2D IC by cell-centroid LONGITUDE, with an
optional TWO-STAGE gradient about a reference longitude:

    west model limit  --stage 1-->  reference lon  --stage 2-->  east model limit
    value:  west            ->          ref               ->          east_edge

Per variable you give (west, ref, east_edge):
  - stage 1 (lon <= ref_lon): linear  west  -> ref   between the western limit and ref_lon
  - stage 2 (lon  > ref_lon): linear  ref   -> east_edge  between ref_lon and the eastern limit
    ...or, if east_edge is None, HOLD 'ref' east of the reference (single-stage / 1992-style).

Optional `stage2_region` (an MLAU BP_Region name, e.g. 'Swan Canning') CONFINES the stage-2
freshening to cells inside that region; all other cells east of ref_lon HOLD 'ref'. Use this
so the estuary grades down to east_edge while marine embayments (e.g. eastern Cockburn Sound)
stay at the stage-1/ref value.

All other IC columns (WL, U, V, WQ) are passed through unchanged. The IC row order is the
model cell-ID order; cell longitude comes from the run's `cell_X` (identical across runs on
the same mesh).

Usage:   python make_graded_ic.py 1991        # -> initial_condition_2D_Aug_B010_Sgrad.csv
         python make_graded_ic.py 1992        # -> reproduces initial_condition_2D_Mar_B010_Sgrad.csv
Config lives in CONFIGS below — add a new step by copying a block.
"""
import sys, numpy as np, pandas as pd, xarray as xr, warnings
warnings.filterwarnings('ignore')

IC_DIR = r'S:/Matt_Working/csiem/model_components/includes/ic'
# any run on the same mesh works (cell_X is identical run-to-run)
NC = {
    '1991': r'S:/Matt_Working/csiem/output_archive/1.7.0/1991_aug/csiem_B010_19910720_19910831.nc',
    '1992': r'S:/Matt_Working/csiem/output_archive/1.7.0/1992_marmay/csiem_B010_19920222_19920531.nc',
}

# value dicts: west = value at the WESTERN model limit, ref = value at ref_lon,
# east_edge = value at the EASTERN model limit (None => hold 'ref' east of ref_lon).
CONFIGS = {
    # ---- 1991 (Aug, winter): cooler/fresher toward the coast, + a 2nd salinity stage
    #      that grades down into the Swan estuary at the far eastern model edge.
    '1991': dict(
        base='initial_condition_2D_Aug_B010.csv',
        out='initial_condition_2D_Aug_B010_Sgrad.csv',
        ref_lon=115.75,
        stage2_region='Swan Canning',                    # confine the 34->20 stage to the estuary
        # ITER4: breakpoint profile through 5 control lons (saltier shelf/coast, estuary drop past ref)
        # ITER6: more aggressive estuary drop (fresher OA) - shelf/ref held, estuary 20/13 -> 13/5
        SAL=dict(bp_lon=[115.331, 115.65, 115.75, 115.80, 115.854],
                 bp_val=[36.10,   35.10,  34.65,  13.0,   5.0], ref_idx=2),  # ends pinned to model limits
        TEMP=dict(west=19.4, ref=15.0, east_edge=14.0),  # ITER10: more aggressive eastern+estuary cool -> 19.4 (ocean) -> 15.0 (coast) -> 14.0 (Swan estuary) [was 15.4 / 15.2]
    ),
    # ---- 1992 (Mar, summer): saltier/warmer toward the coast, held east of ref.
    #      Reproduces the existing initial_condition_2D_Mar_B010_Sgrad.csv.
    '1992': dict(
        base='initial_condition_2D_Mar_B010.csv',
        out='initial_condition_2D_Mar_B010_Sgrad.csv',
        ref_lon=115.75,
        SAL=dict(west=35.80, ref=36.25, east_edge=None),
        TEMP=dict(west=20.9, ref=23.2, east_edge=None),
    ),
}


def grade(cellx, lon_west, lon_east, ref_lon, spec, stage2_mask=None):
    """Two-stage piecewise-linear value by longitude (see module docstring).
    stage2_mask (optional bool array): cells allowed to take the stage-2 (ref->east_edge)
    gradient; east-of-ref cells outside the mask HOLD 'ref'."""
    west, ref, east_edge = spec['west'], spec['ref'], spec.get('east_edge')
    out = np.empty(len(cellx), float)
    w = cellx <= ref_lon
    out[w] = west + np.clip((cellx[w] - lon_west) / (ref_lon - lon_west), 0, 1) * (ref - west)
    out[~w] = ref                                          # default east of ref: hold ref
    if east_edge is not None:
        s2 = ~w if stage2_mask is None else (~w & stage2_mask)
        out[s2] = ref + np.clip((cellx[s2] - ref_lon) / (lon_east - ref_lon), 0, 1) * (east_edge - ref)
    return out


def grade_breakpoints(cellx, lon_west, lon_east, ref_lon, spec, stage2_mask=None):
    """Piecewise-linear value through explicit (lon, value) breakpoints. Same stage2_region
    confinement as grade(): east-of-ref cells outside the mask HOLD the ref value. The first /
    last breakpoint longitudes are pinned to the actual model limits.
    spec: dict(bp_lon=[...], bp_val=[...], ref_idx=<index of ref_lon in the breakpoint arrays>)."""
    bl = list(spec['bp_lon']); bv = list(spec['bp_val']); ri = spec['ref_idx']; ref = bv[ri]
    bl[0], bl[-1] = lon_west, lon_east                    # pin ends to true model limits
    out = np.empty(len(cellx), float)
    w = cellx <= ref_lon
    out[w] = np.interp(cellx[w], bl[:ri + 1], bv[:ri + 1])   # west of ref: interp W breakpoints
    out[~w] = ref                                            # east of ref, outside region: hold ref
    s2 = ~w if stage2_mask is None else (~w & stage2_mask)
    out[s2] = np.interp(cellx[s2], bl[ri:], bv[ri:])         # east of ref, in region: interp E breakpoints
    return out


def grade_var(cellx, lon_west, lon_east, ref_lon, spec, mask):
    """Dispatch: use breakpoint grading if spec has bp_lon, else the two-stage west/ref/east_edge."""
    fn = grade_breakpoints if 'bp_lon' in spec else grade
    return fn(cellx, lon_west, lon_east, ref_lon, spec, mask)


def _region_mask(cellx, celly, region_name):
    """Bool array: cells whose centroid falls inside the dissolved MLAU BP_Region."""
    import geopandas as gpd, shapely.vectorized as sv
    z = gpd.read_file(r'G:/CSIEM/1.7.0/csiem-marvl/gis/Zones/MLAU_Zones_v3_ll.shp')
    poly = z.dissolve(by='BP_Region').loc[region_name, 'geometry']
    return sv.contains(poly, cellx, celly)


def build(step, out_override=None, verbose=True):
    cfg = CONFIGS[step]
    ic = pd.read_csv(f'{IC_DIR}/{cfg["base"]}', skipinitialspace=True)
    ds = xr.open_dataset(NC[step]); cellx = ds['cell_X'].values; celly = ds['cell_Y'].values
    assert len(ic) == len(cellx), f'IC rows {len(ic)} != model cells {len(cellx)}'
    assert {'SAL', 'TEMP'} <= set(ic.columns), f'base IC missing SAL/TEMP: {list(ic.columns)}'
    lon_west, lon_east = float(cellx.min()), float(cellx.max())
    mask = None
    if cfg.get('stage2_region'):
        mask = _region_mask(cellx, celly, cfg['stage2_region'])
        if verbose: print(f'   stage2_region={cfg["stage2_region"]!r}: {int(mask.sum())} cells')
    ic['SAL'] = np.round(grade_var(cellx, lon_west, lon_east, cfg['ref_lon'], cfg['SAL'], mask), 4)
    ic['TEMP'] = np.round(grade_var(cellx, lon_west, lon_east, cfg['ref_lon'], cfg['TEMP'], mask), 4)
    outp = f'{IC_DIR}/{out_override or cfg["out"]}'
    ic.to_csv(outp, index=False)
    if verbose:
        rl = cfg['ref_lon']
        print(f'[{step}] base={cfg["base"]} cells={len(ic)} lon {lon_west:.3f}..{lon_east:.3f} ref={rl}')
        print(f'   SAL  {cfg["SAL"]}')
        print(f'   TEMP {cfg["TEMP"]}')
        for tgt in [lon_west, 115.50, 115.65, rl - 1e-4, rl + 1e-4, 115.80, lon_east]:
            i = int(np.argmin(np.abs(cellx - tgt)))
            print(f'   lon {cellx[i]:.4f} -> SAL {ic["SAL"].iloc[i]:6.3f}  TEMP {ic["TEMP"].iloc[i]:6.3f}')
        e = cellx > rl
        print(f'   cells east of ref ({rl}): {int(e.sum())}  '
              f'SAL range {ic["SAL"][e].min():.2f}..{ic["SAL"][e].max():.2f}')
        print('wrote', outp)
    return ic


if __name__ == '__main__':
    step = sys.argv[1] if len(sys.argv) > 1 else '1991'
    build(step)
