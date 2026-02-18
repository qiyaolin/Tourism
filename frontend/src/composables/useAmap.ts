import AMapLoader from "@amap/amap-jsapi-loader";
import { ref, type Ref } from "vue";
import type { ItineraryItemWithPoi } from "../api";

type MarkerClickHandler = (item: ItineraryItemWithPoi) => void;
type AmapMarker = {
  on: (eventName: string, listener: () => void) => void;
  setAnimation?: (animation: string | null) => void;
  setzIndex?: (zIndex: number) => void;
  getPosition: () => unknown;
};

type AmapMap = {
  add: (marker: AmapMarker) => void;
  remove: (marker: AmapMarker) => void;
  setFitView: (
    overlays?: unknown,
    immediately?: boolean,
    avoid?: [number, number, number, number],
    maxZoom?: number
  ) => void;
  setCenter: (position: unknown) => void;
  destroy: () => void;
};

type AmapApi = {
  Map: new (
    container: HTMLElement,
    options: { zoom: number; center: [number, number]; mapStyle: string }
  ) => AmapMap;
  Marker: new (options: {
    position: [number, number];
    title: string;
    offset: unknown;
    label: { content: string; direction: string };
  }) => AmapMarker;
  Pixel: new (x: number, y: number) => unknown;
};

let amapPromise: Promise<AmapApi> | null = null;

function loadAmap() {
  const key = import.meta.env.VITE_AMAP_KEY;
  if (!key) {
    throw new Error("VITE_AMAP_KEY is missing");
  }
  if (!amapPromise) {
    amapPromise = AMapLoader.load({
      key,
      version: "2.0"
    }) as Promise<AmapApi>;
  }
  return amapPromise;
}

export function useAmap(containerRef: Ref<HTMLElement | null>) {
  const mapReady = ref(false);
  const markersByItemId = new Map<string, AmapMarker>();
  let mapInstance: AmapMap | null = null;
  let amapApi: AmapApi | null = null;
  let selectedMarker: AmapMarker | null = null;

  function callMarkerMethod(
    marker: AmapMarker,
    method: "setAnimation" | "setzIndex",
    arg: unknown
  ) {
    const fn = marker[method];
    if (typeof fn !== "function") {
      return;
    }
    try {
      // Keep `this` bound to marker instance; detached calls can break AMap internals.
      (fn as (this: AmapMarker, value: unknown) => void).call(marker, arg);
    } catch (error) {
      console.warn(`[AMap] marker method ${method} failed`, error);
    }
  }

  async function initMap() {
    if (mapInstance) {
      return;
    }
    amapApi = await loadAmap();
    if (!containerRef.value) {
      throw new Error("Map container is not ready");
    }
    mapInstance = new amapApi.Map(containerRef.value, {
      zoom: 11,
      center: [116.397428, 39.90923],
      mapStyle: "amap://styles/normal"
    });
    mapReady.value = true;
  }

  function clearMarkers() {
    if (!mapInstance) {
      return;
    }
    for (const marker of markersByItemId.values()) {
      mapInstance.remove(marker);
    }
    markersByItemId.clear();
    selectedMarker = null;
  }

  function renderMarkers(items: ItineraryItemWithPoi[], onClick: MarkerClickHandler) {
    if (!mapInstance || !amapApi) {
      return;
    }
    clearMarkers();
    if (items.length === 0) {
      return;
    }

    for (const item of items) {
      const marker = new amapApi.Marker({
        position: [item.poi.longitude, item.poi.latitude],
        title: item.poi.name,
        offset: new amapApi.Pixel(-13, -30),
        label: {
          content: `<div class="atlas-marker-label">D${item.day_index}-${item.sort_order}</div>`,
          direction: "top"
        }
      });
      marker.on("click", () => onClick(item));
      mapInstance.add(marker);
      markersByItemId.set(item.item_id, marker);
    }
    mapInstance.setFitView(undefined, false, [70, 70, 70, 70], 14);
  }

  function focusMarker(itemId: string) {
    if (!mapInstance) {
      return;
    }
    const marker = markersByItemId.get(itemId);
    if (!marker) {
      return;
    }
    if (selectedMarker && selectedMarker !== marker) {
      callMarkerMethod(selectedMarker, "setAnimation", null);
      callMarkerMethod(selectedMarker, "setzIndex", 10);
    }
    selectedMarker = marker;
    callMarkerMethod(marker, "setzIndex", 200);
    callMarkerMethod(marker, "setAnimation", "AMAP_ANIMATION_BOUNCE");
    mapInstance.setCenter(marker.getPosition());
  }

  function destroyMap() {
    clearMarkers();
    if (mapInstance) {
      mapInstance.destroy();
      mapInstance = null;
    }
    amapApi = null;
    mapReady.value = false;
  }

  return {
    mapReady,
    initMap,
    renderMarkers,
    focusMarker,
    clearMarkers,
    destroyMap
  };
}
