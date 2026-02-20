<script setup lang="ts">
import type { ItineraryItemWithPoi } from "../api";
import PoiCorrectionPanel from "./PoiCorrectionPanel.vue";

defineProps<{
  item: ItineraryItemWithPoi;
  token?: string;
  sourceItineraryId?: string | null;
}>();
</script>

<template>
  <article class="poi-card">
    <header class="poi-card-header">
      <p class="poi-badge">D{{ item.day_index }} - {{ item.sort_order }}</p>
      <h3>{{ item.poi.name }}</h3>
      <p class="poi-type">{{ item.poi.type }}</p>
    </header>

    <dl class="poi-meta">
      <div>
        <dt>地址</dt>
        <dd>{{ item.poi.address || "未提供" }}</dd>
      </div>
      <div>
        <dt>营业时间</dt>
        <dd>{{ item.poi.opening_hours || "未提供" }}</dd>
      </div>
      <div>
        <dt>参考票价</dt>
        <dd>{{ item.poi.ticket_price == null ? "未提供" : `¥${item.poi.ticket_price}` }}</dd>
      </div>
      <div>
        <dt>停留时长</dt>
        <dd>{{ item.duration_minutes == null ? "未提供" : `${item.duration_minutes} 分钟` }}</dd>
      </div>
      <div>
        <dt>开始时间</dt>
        <dd>{{ item.start_time || "未提供" }}</dd>
      </div>
      <div>
        <dt>预算花费</dt>
        <dd>{{ item.cost == null ? "未提供" : `¥${item.cost}` }}</dd>
      </div>
    </dl>

    <section class="poi-ticket-rules" v-if="item.poi.ticket_rules.length > 0">
      <h4>票价规则</h4>
      <ul>
        <li v-for="rule in item.poi.ticket_rules" :key="rule.id">
          {{ rule.audience_label }} / {{ rule.ticket_type }} / {{ rule.time_slot }}：¥{{ rule.price }}
          <span v-if="rule.conditions">（{{ rule.conditions }}）</span>
        </li>
      </ul>
    </section>

    <p v-if="item.tips" class="poi-tips">{{ item.tips }}</p>

    <PoiCorrectionPanel
      v-if="token"
      :poi-id="item.poi.id"
      :poi-name="item.poi.name"
      :token="token"
      :source-itinerary-id="sourceItineraryId"
    />
  </article>
</template>
