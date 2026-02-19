<script setup lang="ts">
defineProps<{
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  (e: "confirm"): void;
  (e: "cancel"): void;
}>();

function onMaskClick() {
  emit("cancel");
}

function onDialogClick(event: MouseEvent) {
  event.stopPropagation();
}
</script>

<template>
  <div
    v-if="open"
    class="dialog-backdrop"
    @click="onMaskClick"
  >
    <section
      class="dialog-card"
      @click="onDialogClick"
    >
      <h3>{{ title }}</h3>
      <p class="subtle">
        {{ message }}
      </p>
      <div class="action-row">
        <button
          class="btn ghost"
          :disabled="loading"
          @click="emit('cancel')"
        >
          {{ cancelText || "取消" }}
        </button>
        <button
          class="btn"
          :class="danger ? 'danger' : 'primary'"
          :disabled="loading"
          @click="emit('confirm')"
        >
          {{ loading ? "处理中..." : (confirmText || "确认") }}
        </button>
      </div>
    </section>
  </div>
</template>
