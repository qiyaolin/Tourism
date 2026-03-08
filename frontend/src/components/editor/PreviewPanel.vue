<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { ItineraryItemWithPoi } from "../../api";
import { useAmap } from "../../composables/useAmap";
import type { Block, BlockType } from "../../types/block";
import { BLOCK_TYPE_CONFIGS } from "../../types/block";

const props = withDefaults(
  defineProps<{
    selectedBlock: Block | null;
    mapItems: ItineraryItemWithPoi[];
    focusedBlockId?: string;
    mapLoading?: boolean;
  }>(),
  {
    focusedBlockId: "",
    mapLoading: false
  }
);

const mapHost = ref<HTMLElement | null>(null);
const localMapLoading = ref(false);
const localMapError = ref("");
const mapInitialized = ref(false);

const { mapReady, initMap, renderMarkers, focusMarker, clearMarkers, destroyMap } = useAmap(mapHost);

const config = computed(() => {
  if (!props.selectedBlock) return null;
  return BLOCK_TYPE_CONFIGS[props.selectedBlock.blockType as BlockType] ?? BLOCK_TYPE_CONFIGS.scenic;
});

const mapBusy = computed(() => props.mapLoading || localMapLoading.value || !mapInitialized.value);
const selectedBlockHasLocation = computed(
  () =>
    props.selectedBlock &&
    Number.isFinite(props.selectedBlock.longitude) &&
    Number.isFinite(props.selectedBlock.latitude)
);

function formatDuration(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}小时${m > 0 ? `${m}分钟` : ""}` : `${m}分钟`;
}

function syncMapState() {
  if (!mapReady.value) return;
  if (props.mapItems.length === 0) {
    clearMarkers();
    return;
  }
  renderMarkers(props.mapItems, () => {
    // Map click to select is intentionally disabled in V2.
  });
  if (props.focusedBlockId) {
    focusMarker(props.focusedBlockId);
  }
}

onMounted(async () => {
  localMapLoading.value = true;
  localMapError.value = "";
  try {
    await initMap();
    mapInitialized.value = true;
    syncMapState();
  } catch (error) {
    localMapError.value = error instanceof Error ? error.message : "地图初始化失败";
  } finally {
    localMapLoading.value = false;
  }
});

watch(
  () => props.mapItems,
  () => {
    syncMapState();
  },
  { deep: true }
);

watch(
  () => props.focusedBlockId,
  (nextId) => {
    if (!nextId || !mapReady.value) return;
    focusMarker(nextId);
  }
);

onBeforeUnmount(() => {
  destroyMap();
  mapInitialized.value = false;
});
</script>

<template>
  <div class="preview-panel">
    <div class="preview-panel__map">
      <div ref="mapHost" class="map-host" />
      <div v-if="localMapError" class="map-overlay error">{{ localMapError }}</div>
      <div v-else-if="mapBusy" class="map-overlay">地图加载中...</div>
      <div v-else-if="mapItems.length === 0" class="map-overlay">当前没有可定位节点</div>
    </div>

    <div
      v-if="selectedBlock && config"
      class="preview-panel__detail"
      :style="{ '--pd-color': config.color, '--pd-bg': config.bgColor }"
    >
      <div class="detail-header">
        <span class="detail-icon">{{ config.icon }}</span>
        <div class="detail-title-group">
          <h3 class="detail-title">{{ selectedBlock.title }}</h3>
          <span class="detail-type-badge" :style="{ background: config.color }">{{ config.label }}</span>
        </div>
      </div>

      <div class="detail-grid">
        <div v-if="selectedBlock.durationMinutes" class="detail-row">
          <span class="detail-label">时长</span>
          <span class="detail-value">{{ formatDuration(selectedBlock.durationMinutes) }}</span>
        </div>
        <div v-if="selectedBlock.cost != null" class="detail-row">
          <span class="detail-label">费用</span>
          <span class="detail-value">¥{{ selectedBlock.cost }}</span>
        </div>
        <div v-if="selectedBlock.address" class="detail-row detail-row-full">
          <span class="detail-label">地址</span>
          <span class="detail-value">{{ selectedBlock.address }}</span>
        </div>
      </div>

      <div v-if="selectedBlock.typeData" class="detail-extra">
        <div v-for="(value, key) in selectedBlock.typeData" :key="String(key)" class="detail-row detail-row-full">
          <span class="detail-label">{{ String(key) }}</span>
          <span class="detail-value">{{ String(value) }}</span>
        </div>
      </div>

      <p v-if="selectedBlock.tips" class="detail-note">备注：{{ selectedBlock.tips }}</p>
      <p v-if="selectedBlock && !selectedBlockHasLocation" class="detail-note">
        该节点暂无坐标，地图保持当前视角。
      </p>
    </div>

    <div v-else class="preview-panel__empty">选择时间轴节点后显示地图详情</div>
  </div>
</template>

<style scoped>
.preview-panel {
  display: grid;
  grid-template-rows: minmax(130px, 1fr) auto;
  height: 100%;
  background: #0f1728;
  color: #eaf1ff;
}

.preview-panel__map {
  position: relative;
  min-height: 130px;
  border-bottom: 1px solid rgba(234, 241, 255, 0.12);
}

.map-host {
  width: 100%;
  height: 100%;
}

.map-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(5, 9, 18, 0.7);
  color: #d8e6ff;
  font-size: 12px;
}

.map-overlay.error {
  color: #ffb4b4;
}

.preview-panel__detail {
  padding: 10px;
  background: #101b30;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-icon {
  font-size: 22px;
}

.detail-title-group {
  min-width: 0;
}

.detail-title {
  margin: 0;
  font-size: 14px;
  line-height: 1.3;
  color: #f4f8ff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-type-badge {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: #f8fbff;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 10px;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-row-full {
  grid-column: 1 / -1;
}

.detail-label {
  font-size: 11px;
  color: #9fb3d9;
}

.detail-value {
  font-size: 12px;
  color: #edf4ff;
  word-break: break-word;
}

.detail-extra {
  border-top: 1px dashed rgba(234, 241, 255, 0.18);
  padding-top: 6px;
  display: grid;
  gap: 4px;
}

.detail-note {
  margin: 0;
  font-size: 12px;
  color: #b4c8eb;
  line-height: 1.4;
}

.preview-panel__empty {
  padding: 12px;
  font-size: 12px;
  color: #9fb3d9;
  background: #101b30;
}
</style>
