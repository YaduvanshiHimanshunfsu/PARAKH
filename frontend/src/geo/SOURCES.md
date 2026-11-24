# Map data sources

`india.topo.json` has two layers:

| Layer | Source | Licence |
|---|---|---|
| `india` (national outline) | DataMeet `Country/india-soi.geojson`: dissolved from official Survey of India / Census of India boundaries, including the full Jammu & Kashmir and Ladakh as on the official map. https://github.com/datameet/maps | CC BY-SA 2.5 / ODbL |
| `states` (36 states and UTs, property `name`) | DataMeet `States/Admin2` shapefile | CC BY 4.0 (DataMeet) |

Attribution shown in the app footer area of map screens: "Boundaries: Survey of India via DataMeet".

## How the file was built (24 Nov 2026)

```text
npx mapshaper -i india-soi.geojson Admin2.shp combine-files \
  -rename-layers india,states \
  -filter-fields ST_NM target=states -rename-fields name=ST_NM target=states \
  -filter-fields '' target=india \
  -simplify 0.3% keep-shapes \
  -filter-islands min-area=40km2 remove-empty target=* \
  -o src/geo/india.topo.json format=topojson quantization=6000 target=*
```

## Known limitations

- The outline is simplified for a decorative hero map (≈160 KB). Do not use it for measurement or for any legal or administrative purpose.
- **District boundaries are not included.** DataMeet's district layer is Census 2011 (33 Rajasthan districts), which does not match today's districts. The officer district choropleth (plan H.7) needs current LGD district boundaries, for example from `ramSeraph/indian_admin_boundaries` (CC0) or the state GIS portal. It is built once cases carry a victim district (Phase C).
- Verify the outline against the latest official Survey of India map before any public deployment.
