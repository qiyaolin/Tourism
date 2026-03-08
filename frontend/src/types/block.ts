export type BlockType = "scenic" | "dining" | "lodging" | "transit" | "note" | "shopping" | "activity";
export type BlockStatus = "draft" | "ready" | "running" | "done" | "blocked";
export type BlockPriority = "low" | "medium" | "high";
export type BlockRiskLevel = "low" | "medium" | "high";
export type BlockEdgeType = "hard" | "soft";

export type LaneKey =
  | "core"
  | "transit"
  | "scenic"
  | "dining"
  | "lodging"
  | "activity"
  | "note"
  | "shopping";

export interface LaneDefinition {
  key: LaneKey | string;
  label: string;
  icon: string;
}

export const DEFAULT_LANES: LaneDefinition[] = [
  { key: "core", label: "核心流程", icon: "◆" },
  { key: "transit", label: "交通", icon: "↔" },
  { key: "scenic", label: "景点", icon: "◉" },
  { key: "dining", label: "餐饮", icon: "◍" },
  { key: "lodging", label: "住宿", icon: "▣" },
  { key: "activity", label: "活动", icon: "✦" },
  { key: "note", label: "备注", icon: "✎" },
  { key: "shopping", label: "购物", icon: "◈" },
];

export interface BlockTypeConfig {
  type: BlockType;
  label: string;
  icon: string;
  color: string;
  bgColor: string;
  borderColor: string;
  fields: string[];
}

export const BLOCK_TYPE_CONFIGS: Record<BlockType, BlockTypeConfig> = {
  scenic: {
    type: "scenic",
    label: "景点",
    icon: "◉",
    color: "#4E9DFF",
    bgColor: "rgba(78, 157, 255, 0.12)",
    borderColor: "#4E9DFF",
    fields: ["opening_hours", "ticket_price", "highlights", "photo_spots"],
  },
  dining: {
    type: "dining",
    label: "餐饮",
    icon: "◍",
    color: "#F2A541",
    bgColor: "rgba(242, 165, 65, 0.12)",
    borderColor: "#F2A541",
    fields: ["per_capita", "cuisine_type", "recommended_dishes", "reservation_info"],
  },
  lodging: {
    type: "lodging",
    label: "住宿",
    icon: "▣",
    color: "#7A78FF",
    bgColor: "rgba(122, 120, 255, 0.12)",
    borderColor: "#7A78FF",
    fields: ["room_type", "price_per_night", "check_in_time", "check_out_time"],
  },
  transit: {
    type: "transit",
    label: "交通",
    icon: "↔",
    color: "#34C47C",
    bgColor: "rgba(52, 196, 124, 0.12)",
    borderColor: "#34C47C",
    fields: ["from_title", "to_title", "method", "line_info", "distance_km"],
  },
  note: {
    type: "note",
    label: "备注",
    icon: "✎",
    color: "#A6AFBD",
    bgColor: "rgba(166, 175, 189, 0.12)",
    borderColor: "#A6AFBD",
    fields: ["content_markdown"],
  },
  shopping: {
    type: "shopping",
    label: "购物",
    icon: "◈",
    color: "#E86EA3",
    bgColor: "rgba(232, 110, 163, 0.12)",
    borderColor: "#E86EA3",
    fields: ["shop_name", "products", "business_hours"],
  },
  activity: {
    type: "activity",
    label: "活动",
    icon: "✦",
    color: "#FF6A4D",
    bgColor: "rgba(255, 106, 77, 0.12)",
    borderColor: "#FF6A4D",
    fields: ["event_name", "time_slot", "booking_method"],
  },
};

export interface BlockDependency {
  id: string;
  itineraryId: string;
  fromBlockId: string;
  toBlockId: string;
  edgeType: BlockEdgeType;
  createdAt: string;
}

export interface Block {
  id: string;
  itineraryId: string;
  parentBlockId: string | null;
  sortOrder: number;
  dayIndex: number;
  laneKey: string;
  startMinute: number | null;
  endMinute: number | null;
  blockType: BlockType;
  title: string;
  durationMinutes: number | null;
  cost: number | null;
  tips: string | null;
  longitude: number | null;
  latitude: number | null;
  address: string | null;
  photos: string[] | null;
  typeData: Record<string, unknown> | null;
  isContainer: boolean;
  sourceTemplateId: string | null;
  status: BlockStatus;
  priority: BlockPriority;
  riskLevel: BlockRiskLevel;
  assigneeUserId: string | null;
  tags: string[] | null;
  uiMeta: Record<string, unknown> | null;
  children: Block[];
  createdAt: string;
  updatedAt: string;
}

export interface BlockCreate {
  parentBlockId?: string | null;
  sortOrder?: number;
  dayIndex?: number;
  laneKey?: string;
  startMinute?: number | null;
  endMinute?: number | null;
  blockType: BlockType;
  title: string;
  durationMinutes?: number | null;
  cost?: number | null;
  tips?: string | null;
  longitude?: number | null;
  latitude?: number | null;
  address?: string | null;
  photos?: string[] | null;
  typeData?: Record<string, unknown> | null;
  isContainer?: boolean;
  sourceTemplateId?: string | null;
  status?: BlockStatus;
  priority?: BlockPriority;
  riskLevel?: BlockRiskLevel;
  assigneeUserId?: string | null;
  tags?: string[] | null;
  uiMeta?: Record<string, unknown> | null;
}

export interface BlockUpdate {
  parentBlockId?: string | null;
  sortOrder?: number;
  dayIndex?: number;
  laneKey?: string;
  startMinute?: number | null;
  endMinute?: number | null;
  blockType?: BlockType;
  title?: string;
  durationMinutes?: number | null;
  cost?: number | null;
  tips?: string | null;
  longitude?: number | null;
  latitude?: number | null;
  address?: string | null;
  photos?: string[] | null;
  typeData?: Record<string, unknown> | null;
  isContainer?: boolean;
  status?: BlockStatus;
  priority?: BlockPriority;
  riskLevel?: BlockRiskLevel;
  assigneeUserId?: string | null;
  tags?: string[] | null;
  uiMeta?: Record<string, unknown> | null;
}

export interface BlockReorder {
  parentBlockId: string | null;
  dayIndex: number;
  orderedBlockIds: string[];
}

export interface BlockTemplate {
  id: string;
  authorId: string;
  authorNickname: string | null;
  title: string;
  description: string | null;
  styleTags: string[] | null;
  blockType: string;
  isGroup: boolean;
  contentSnapshot: Record<string, unknown> | null;
  childrenSnapshot: Record<string, unknown>[] | null;
  forkCount: number;
  ratingAvg: number | null;
  ratingCount: number;
  status: string;
  regionName: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TemplatePublish {
  title: string;
  description?: string | null;
  styleTags?: string[] | null;
  blockType: string;
  isGroup?: boolean;
  contentSnapshot?: Record<string, unknown> | null;
  childrenSnapshot?: Record<string, unknown>[] | null;
  longitude?: number | null;
  latitude?: number | null;
  regionName?: string | null;
}

export interface TemplateFork {
  itineraryId: string;
  dayIndex?: number;
  sortOrder?: number;
  parentBlockId?: string | null;
}

export interface TemplateRating {
  score: number;
  comment?: string | null;
}
