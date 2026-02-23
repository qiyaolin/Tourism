import type { TimelineDraftItem } from "../types/timeline";

export type DiffChange = {
    type: "modify" | "add" | "delete" | "reorder";
    targetName: string;
    description: string;
};

const FIELD_NAMES: Record<string, string> = {
    startTime: "开始时间",
    durationMinutes: "停留时长",
    cost: "预算花费",
    tips: "备注",
};

export function computeDraftItemsDiff(
    oldItems: TimelineDraftItem[],
    newItems: TimelineDraftItem[]
): DiffChange[] {
    const changes: DiffChange[] = [];
    const oldMap = new Map(oldItems.map((item) => [item.clientId, item]));
    const newMap = new Map(newItems.map((item) => [item.clientId, item]));

    // Look for Adds and Modifies
    for (const newItem of newItems) {
        const oldItem = oldMap.get(newItem.clientId);
        const targetName = newItem.poi.name;

        if (!oldItem) {
            changes.push({
                type: "add",
                targetName,
                description: `添加了【${targetName}】`
            });
            continue;
        }

        // Compare fields
        const modifiedFields: string[] = [];
        for (const key of ["startTime", "durationMinutes", "cost", "tips"] as const) {
            if (oldItem[key] !== newItem[key]) {
                const oldVal = oldItem[key] ?? "空";
                const newVal = newItem[key] ?? "空";
                modifiedFields.push(`将【${FIELD_NAMES[key]}】从 ${oldVal} 修改为 ${newVal}`);
            }
        }

        if (modifiedFields.length > 0) {
            changes.push({
                type: "modify",
                targetName,
                description: `在【${targetName}】${modifiedFields.join("，")}`
            });
        } else if (
            oldItem.dayIndex !== newItem.dayIndex ||
            oldItem.sortOrder !== newItem.sortOrder
        ) {
            changes.push({
                type: "reorder",
                targetName,
                description: `移动了【${targetName}】的游玩顺序`
            });
        }
    }

    // Look for Deletes
    for (const oldItem of oldItems) {
        if (!newMap.has(oldItem.clientId)) {
            changes.push({
                type: "delete",
                targetName: oldItem.poi.name,
                description: `删除了【${oldItem.poi.name}】`
            });
        }
    }

    return changes;
}
