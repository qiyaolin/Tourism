<script setup lang="ts">
import type { ItineraryDiffResponse } from "../api";

const META_FIELD_LABELS: Record<string, string> = {
  title: "行程标题",
  destination: "目的地",
  days: "行程天数",
  status: "行程状态",
  visibility: "可见范围",
  cover_image_url: "封面图片"
};

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  in_progress: "进行中",
  published: "已发布"
};

const VISIBILITY_LABELS: Record<string, string> = {
  private: "仅自己可见",
  followers: "关注者可见",
  public: "公开可见"
};

defineProps<{
  open: boolean;
  loading: boolean;
  error: string;
  diff: ItineraryDiffResponse | null;
}>();

function formatMetaFieldLabel(field: string): string {
  return META_FIELD_LABELS[field] ?? `其他信息（${field}）`;
}

function isBlank(value: unknown): boolean {
  return value === null || value === undefined || (typeof value === "string" && value.trim() === "");
}

function formatMetaValue(field: string, value: unknown): string {
  if (isBlank(value)) {
    return "未设置";
  }

  if (field === "status" && typeof value === "string") {
    return STATUS_LABELS[value] ?? value;
  }

  if (field === "visibility" && typeof value === "string") {
    return VISIBILITY_LABELS[value] ?? value;
  }

  if (field === "cover_image_url") {
    return "已设置封面链接";
  }

  if (field === "days" && typeof value === "number") {
    return `${value} 天`;
  }

  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
</script>

<template>
  <section
    v-if="open"
    class="panel-card diff-panel"
  >
    <h3>修改对比</h3>
    <p class="subtle">
      绿色=新增，红色=删除，黄色=修改
    </p>

    <p
      v-if="loading"
      class="subtle"
    >
      正在加载差异数据...
    </p>
    <p
      v-else-if="error"
      class="error"
    >
      {{ error }}
    </p>
    <template v-else-if="diff">
      <div class="diff-summary">
        <span class="diff-badge added">新增 {{ diff.summary.added }}</span>
        <span class="diff-badge removed">删除 {{ diff.summary.removed }}</span>
        <span class="diff-badge modified">修改 {{ diff.summary.modified }}</span>
      </div>

      <div
        v-if="diff.metadata_diffs.length > 0"
        class="diff-section"
      >
        <h4>行程元信息</h4>
        <article
          v-for="entry in diff.metadata_diffs"
          :key="`meta-${entry.field}`"
          class="diff-line modified"
        >
          <p class="diff-field">
            {{ formatMetaFieldLabel(entry.field) }}
          </p>
          <p class="diff-change">
            <span
              class="diff-before"
              :title="formatMetaValue(entry.field, entry.before)"
            >{{ formatMetaValue(entry.field, entry.before) }}</span>
            <span class="diff-arrow">→</span>
            <span
              class="diff-after"
              :title="formatMetaValue(entry.field, entry.after)"
            >{{ formatMetaValue(entry.field, entry.after) }}</span>
          </p>
        </article>
      </div>

      <div
        v-if="diff.added_items.length > 0"
        class="diff-section"
      >
        <h4>新增节点</h4>
        <article
          v-for="entry in diff.added_items"
          :key="`added-${entry.key}`"
          class="diff-line added"
        >
          <p class="diff-field">
            {{ entry.key }}
          </p>
          <p class="diff-change">
            {{ String(entry.current.poi_name || entry.current.poi_id || "新增节点") }}
          </p>
        </article>
      </div>

      <div
        v-if="diff.removed_items.length > 0"
        class="diff-section"
      >
        <h4>删除节点</h4>
        <article
          v-for="entry in diff.removed_items"
          :key="`removed-${entry.key}`"
          class="diff-line removed"
        >
          <p class="diff-field">
            {{ entry.key }}
          </p>
          <p class="diff-change">
            {{ String(entry.source.poi_name || entry.source.poi_id || "删除节点") }}
          </p>
        </article>
      </div>

      <div
        v-if="diff.modified_items.length > 0"
        class="diff-section"
      >
        <h4>修改节点</h4>
        <article
          v-for="entry in diff.modified_items"
          :key="`modified-${entry.key}`"
          class="diff-line modified"
        >
          <p class="diff-field">
            {{ entry.key }}
          </p>
          <p
            v-for="field in entry.fields"
            :key="`${entry.key}-${field.field}`"
            class="diff-change"
          >
            <strong>{{ field.field }}：</strong>
            <span class="diff-before">{{ String(field.before) }}</span>
            <span class="diff-arrow">→</span>
            <span class="diff-after">{{ String(field.after) }}</span>
          </p>
        </article>
      </div>

      <p
        v-if="
          diff.metadata_diffs.length === 0 &&
            diff.added_items.length === 0 &&
            diff.removed_items.length === 0 &&
            diff.modified_items.length === 0
        "
        class="subtle"
      >
        当前副本与源快照无差异。
      </p>
    </template>
  </section>
</template>
