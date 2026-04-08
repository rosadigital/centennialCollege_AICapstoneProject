import { useEffect, useMemo, useRef } from 'react';
import maplibregl, { GeoJSONSource, Map, Popup } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { HeatmapPoint } from '../lib/api';

type HeatmapMapProps = {
  points: HeatmapPoint[];
};

export function HeatmapMap({ points }: HeatmapMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const popupRef = useRef<Popup | null>(null);

  const featureCollection = useMemo(
    () => ({
      type: 'FeatureCollection' as const,
      features: points.map((point) => ({
        type: 'Feature' as const,
        properties: {
          weight: point.weight,
          delay: point.pred_delay_mean,
          p90: point.pred_delay_p90,
          nEvents: point.n_events,
          delayLabel: `${Math.round(point.pred_delay_mean)} min`,
        },
        geometry: {
          type: 'Point' as const,
          coordinates: [point.longitude_bin, point.latitude_bin],
        },
      })),
    }),
    [points],
  );

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    const container = mapContainerRef.current;
    let cancelled = false;

    const CARTO_VOYAGER_STYLE =
      'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json';

    const initMap = async () => {
      const res = await fetch(CARTO_VOYAGER_STYLE);
      const style = (await res.json()) as Record<string, unknown>;
      // MapLibre v5 + some remote GL styles omit `projection`, which breaks migrateProjection.
      if (style.projection == null) {
        style.projection = { type: 'mercator' };
      }
      if (cancelled) return;

      const map = new maplibregl.Map({
        container,
        style: style as maplibregl.StyleSpecification,
        center: [-79.3832, 43.6532],
        zoom: 10,
      });
      map.addControl(new maplibregl.NavigationControl(), 'top-right');
      popupRef.current = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
      });

      map.on('load', () => {
      map.addSource('delay-points', {
        type: 'geojson',
        data: featureCollection,
      });

      map.addLayer({
        id: 'delay-heatmap',
        type: 'heatmap',
        source: 'delay-points',
        paint: {
          'heatmap-weight': ['interpolate', ['linear'], ['get', 'weight'], 0, 0, 1, 1],
          'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 12, 2.5, 18, 4],
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0,
            'rgba(0, 0, 0, 0)',
            0.2,
            'rgb(103,169,207)',
            0.4,
            'rgb(209,229,240)',
            0.6,
            'rgb(253,219,199)',
            0.8,
            'rgb(239,138,98)',
            1,
            'rgb(178,24,43)',
          ],
          // Keep the heatmap visible on higher zoom levels.
          'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 3, 12, 24, 18, 32],
          'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 0, 0.9, 18, 0.9],
        },
      });

      // Invisible interaction layer to keep hover/popup available at all zoom levels.
      map.addLayer({
        id: 'delay-points-hitbox',
        type: 'circle',
        source: 'delay-points',
        paint: {
          // Larger radius when zoomed out so points are still easy to hover.
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 0, 18, 8, 14, 12, 10, 18, 12],
          'circle-opacity': 0,
          'circle-stroke-opacity': 0,
        },
      });

      // Show point-level circles after a closer zoom.
      map.addLayer({
        id: 'delay-points-circle',
        type: 'circle',
        source: 'delay-points',
        minzoom: 12,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 7, 18, 14],
          'circle-color': [
            'interpolate',
            ['linear'],
            ['get', 'delay'],
            0,
            'rgb(103,169,207)',
            10,
            'rgb(209,229,240)',
            20,
            'rgb(253,219,199)',
            40,
            'rgb(239,138,98)',
            60,
            'rgb(178,24,43)',
          ],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 12, 1.4, 18, 2.4],
          'circle-opacity': ['interpolate', ['linear'], ['zoom'], 12, 0.75, 14, 0.95],
        },
      });

      // Render delay number label at very high zoom.
      map.addLayer({
        id: 'delay-points-label',
        type: 'symbol',
        source: 'delay-points',
        minzoom: 14,
        layout: {
          'text-field': ['get', 'delayLabel'],
          'text-size': ['interpolate', ['linear'], ['zoom'], 14, 14, 18, 20],
          'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
          'text-offset': [0, 1.35],
          'text-anchor': 'top',
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#0b1220',
          'text-halo-width': 2.2,
          'text-halo-blur': 0.4,
        },
      });

      map.on('mouseenter', 'delay-points-hitbox', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'delay-points-hitbox', () => {
        map.getCanvas().style.cursor = '';
        popupRef.current?.remove();
      });
      map.on('mousemove', 'delay-points-hitbox', (event) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== 'Point') return;
        const [lng, lat] = feature.geometry.coordinates as [number, number];
        const props = feature.properties ?? {};
        const delay = Number(props.delay ?? 0).toFixed(2);
        const p90 = Number(props.p90 ?? 0).toFixed(2);
        const nEvents = Number(props.nEvents ?? 0).toLocaleString();
        popupRef.current
          ?.setLngLat([lng, lat])
          .setHTML(
            `<div style="
              font-size:13px;
              line-height:1.45;
              color:#0f172a;
              background:#ffffff;
              padding:10px 12px;
              border-radius:8px;
              box-shadow:0 6px 20px rgba(0,0,0,.18);
              border:1px solid #e2e8f0;
              min-width:220px;">
              <strong style="color:#0b1220">Estimated delay:</strong> ${delay} min<br/>
              <strong style="color:#0b1220">Delay in 90% cases:</strong> ${p90} min<br/>
              <strong style="color:#0b1220">Events:</strong> ${nEvents}
            </div>`,
          )
          .addTo(map);
      });
    });

      mapRef.current = map;
    };

    void initMap();

    return () => {
      cancelled = true;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const source = map.getSource('delay-points') as GeoJSONSource | undefined;
    if (!source) return;
    source.setData(featureCollection);
  }, [featureCollection]);

  return <div ref={mapContainerRef} className="h-[640px] w-full rounded-2xl border border-slate-700" />;
}
