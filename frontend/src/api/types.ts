export interface UserProfile {
  id: number;
  username: string;
  role: "user" | "volunteer" | "dispatcher";
  points: number;
  status_tier: string;
}

export interface PointTransaction {
  id: number;
  amount: number;
  balance_after: number;
  transaction_type: string;
  description: string;
  reference_id: string | null;
  created_at: string;
}

export interface EcoNFT {
  id: number;
  owner_id: number;
  token_id: string;
  svg_content: string;
  title: string;
  creation_date: string;
}

export interface Dashboard {
  profile: UserProfile;
  transactions: PointTransaction[];
  nfts: EcoNFT[];
}

export interface Container {
  id: number;
  device_id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  is_active: boolean;
  last_fill_level: number;
  fill_percent: number;
}

export interface ShopItem {
  id: number;
  title: string;
  description: string;
  price_points: number;
  image_url: string;
  is_active: boolean;
}

export interface PurchaseResponse {
  status: "purchased";
  purchase_id: number;
  user_id: number;
  item_id: number;
  item_title: string;
  spent_points: number;
  points_balance: number;
}

export interface MintResponse {
  status: "minted";
  price_points: number;
  current_balance: number;
  nft: EcoNFT;
}

export interface VolunteerTask {
  id: number;
  title: string;
  reward_points: number;
  date: string;
  time: string;
  description: string;
  status: "open" | "completed";
}

export interface ForumMessage {
  id: number;
  username: string;
  text: string;
  timestamp: string;
}

export interface DetectedObject {
  label: string;
  confidence: number;
  bounding_box: [number, number, number, number];
}

export interface BioResponse {
  analysis_id: number;
  status: "approve" | "reject" | "invalid";
  qr_code: string;
  points_awarded: number;
  current_balance: number;
  detected_objects: DetectedObject[];
  user_id: number;
  image_url: string | null;
  command_sent: boolean;
  action_triggered: "OPEN_LID" | null;
  reason: "mold_detected" | "not_bread" | "empty_frame" | null;
}

export interface DispatchAlert {
  id: number;
  device_id: string | null;
  type: string;
  status: string;
  message: string;
  evidence_url: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface DispatchSummary {
  generated_at: string;
  total_unresolved: number;
  counts_by_type: Record<string, number>;
  counts_by_status: Record<string, number>;
  tasks: DispatchAlert[];
}

export interface DispatchBriefing {
  generated_at: string;
  total_tasks: number;
  text: string;
}

export interface DeviceCommandResponse {
  id: number;
  device_id: string;
  action: "OPEN_LID" | "CLOSE_LID";
  status: "PENDING" | "SENT" | "ACKED" | "FAILED";
  command_sent: boolean;
  idempotency_key: string;
  created_at: string;
}

export interface DeviceTelemetryStatus {
  device_id: string;
  lid_status: string;
  last_seen_at: string;
  temperature_in_c: number | null;
  temperature_out_c: number | null;
  temperature_delta_c: number | null;
  measured_at: string | null;
  camera_stream_url: string | null;
}

export interface CameraStreamUpdate {
  stream_url: string;
}

export interface CameraAnalysis {
  status: "processed";
  frame_id: number;
  device_id: string;
  detected: boolean;
  confidence: number | null;
  detected_objects: DetectedObject[];
  image_url: string;
  alert_id: number | null;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  database: string;
}

export interface AIChatRequest {
  message: string;
  user_id?: string;
}

export interface AIChatResponse {
  response: string;
  provider: "google-gemini" | "offline-fallback";
  model: string | null;
}

export interface RegisterRequest {
  username: string;
  password: string;
  role: "user" | "volunteer";
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface VolunteerRegisterResponse {
  status: "registered";
  user_task_id: number;
  registration_id: number;
  user_id: number;
  task_id: number;
  reward_points_pending: number;
  points_balance: number;
}

export interface VolunteerCompleteResponse {
  status: "completed";
  user_task_id: number;
  user_id: number;
  task_id: number;
  points_awarded: number;
  current_balance: number;
  completed_at: string;
}

export interface ResolveAlertResponse {
  id: number;
  status: "resolved";
  resolved_at: string;
}

export interface FastAPIValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorDetail {
  detail: string | FastAPIValidationError[];
}
