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

export type BreadDecision = "fresh_bread" | "moldy_bread" | "no_bread";

export interface BreadClassification {
  decision: BreadDecision;
  confidence: number;
  probabilities: Record<BreadDecision, number>;
  model: string;
}

export interface BioResponse {
  analysis_id: number;
  status: "approve" | "reject" | "invalid";
  qr_code: string;
  points_awarded: number;
  current_balance: number;
  detected_objects: DetectedObject[];
  classification: BreadClassification | null;
  user_id: number;
  image_url: string | null;
  command_sent: boolean;
  action_triggered: "OPEN_LID" | null;
  reason: "mold_detected" | "not_bread" | "empty_frame" | "low_confidence" | null;
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

/* ---------------------------------------------------------------------------
 * EcoFin — экономический слой
 * ------------------------------------------------------------------------- */

export interface EcoTrips {
  baseline: number;
  actual: number;
  saved: number;
  reduction_percent: number;
  average_fill_at_collection_percent: number | null;
}

export interface EcoResources {
  km_saved: number;
  liters_saved: number;
  co2_kg_saved: number;
}

export interface EcoMoney {
  fuel_kzt: number;
  crew_kzt: number;
  total_kzt: number;
}

/** Стоимость спасённого продукта. Лежит отдельно от денег оператора и
 *  никогда к ним не прибавляется: продукт уже списан, пекарне он не вернётся. */
export interface EcoBread {
  kg_from_citizens: number;
  kg_from_business: number;
  kg_total: number;
  rescued_value_kzt: number;
}

export interface EcoPayback {
  monthly_savings_kzt: number;
  monthly_subscription_kzt: number;
  net_monthly_kzt: number;
  install_total_kzt: number;
  payback_months: number | null;
}

export interface EcoWeeklyPoint {
  week_start: string;
  trips_saved: number;
  kzt_saved: number;
  co2_kg_saved: number;
  /** Неделя ещё не закончилась: её нельзя сравнивать с полными. */
  is_partial: boolean;
}

/** Все входные величины расчёта — по ним раскрывается блок «Откуда цифра». */
export interface EcoFormulaInputs {
  days: number;
  containers: number;
  km_per_stop: number;
  minutes_per_stop: number;
  fuel_consumption_l_per_100km: number;
  fuel_price_kzt_per_liter: number;
  crew_cost_kzt_per_hour: number;
  baseline_trips_per_week: number;
  co2_kg_per_liter: number;
  km_per_saved_stop: number;
  liters_per_saved_stop: number;
  kzt_per_saved_stop: number;
}

/** Один источник дохода вместе с арифметикой, которая его дала. */
export interface RevenueStream {
  key: string;
  title: string;
  monthly_kzt: number;
  /** Строка вида «10 баков × 1 000 ₸» — число проверяется прямо на экране. */
  basis: string;
  note: string;
  /** Маржа на железе разовая и не входит в регулярную выручку. */
  is_recurring: boolean;
}

export interface RevenueScenario {
  title: string;
  containers: number;
  streams: RevenueStream[];
  monthly_recurring_kzt: number;
  one_time_kzt: number;
  annual_recurring_kzt: number;
}

export interface RevenueModel {
  generated_at: string;
  period_start: string;
  period_end: string;
  currency: string;
  pilot: RevenueScenario;
  /** Отсутствует, пока проекцию не запросили: её легко принять за факт. */
  projection: RevenueScenario | null;
  assumptions: string[];
}

export interface SavingsReport {
  generated_at: string;
  period_start: string;
  period_end: string;
  profile_id: number;
  org_name: string;
  city: string;
  containers: number;
  trips: EcoTrips;
  resources: EcoResources;
  money: EcoMoney;
  bread: EcoBread;
  payback: EcoPayback;
  weekly: EcoWeeklyPoint[];
  formula: EcoFormulaInputs;
}

export interface ContainerForecast {
  container_id: number;
  device_id: string;
  name: string;
  latitude: number;
  longitude: number;
  fill_percent: number;
  threshold_percent: number;
  samples: number;
  status: 'due_now' | 'forecast' | 'unavailable';
  rate_percent_per_hour: number | null;
  r_squared: number | null;
  eta_hours: number | null;
  eta_at: string | null;
  reason: 'not_enough_measurements' | 'not_filling' | null;
}

export interface RouteScenario {
  label: string;
  stops: number;
  distance_km: number;
  liters: number;
  kzt: number;
}

export interface RouteLeg {
  position: number;
  from_label: string;
  to_label: string;
  container_id: number | null;
  distance_km: number;
}

export interface RoutePlan {
  generated_at: string;
  horizon_hours: number;
  baseline: RouteScenario;
  planned: RouteScenario;
  distance_saved_km: number;
  liters_saved: number;
  kzt_saved: number;
  co2_kg_saved: number;
  legs: RouteLeg[];
  skipped: string[];
}

export interface ProductForecast {
  product: string;
  expected_kg: number;
  average_kg: number;
  deviation_percent: number;
  samples: number;
  /** same_weekday — прогноз по тому же дню недели; all_days — истории по нему
   *  ещё нет, и ответ честно помечается усреднением по всем дням. */
  basis: 'same_weekday' | 'all_days';
}

export interface WeekdayProfile {
  weekday: number;
  name: string;
  average_kg: number;
  samples: number;
}

export interface BusinessForecast {
  profile_id: number;
  org_name: string;
  target_date: string;
  target_weekday: string;
  lookback_weeks: number;
  products: ProductForecast[];
  weekday_profile: WeekdayProfile[];
  history_days: number;
  total_written_off_kg: number;
  total_donated_kg: number;
  donation_rate_percent: number;
  rescued_value_kzt: number;
}

export interface EcoCostProfile {
  id: number;
  org_name: string;
  city: string;
  km_per_stop: number;
  minutes_per_stop: number;
  fuel_consumption_l_per_100km: number;
  fuel_price_kzt_per_liter: number;
  crew_cost_kzt_per_hour: number;
  baseline_trips_per_week: number;
  fill_threshold_percent: number;
  co2_kg_per_liter: number;
  bread_avg_weight_kg: number;
  bread_cost_kzt_per_kg: number;
  install_price_kzt: number;
  subscription_kzt_per_month: number;
  updated_at: string;
}

export interface WriteOffCreate {
  occurred_on: string;
  product: string;
  kg_written_off: number;
  kg_donated: number;
  cost_kzt_per_kg: number;
}

export interface WriteOffRecord {
  id: number;
  profile_id: number;
  occurred_on: string;
  product: string;
  kg_written_off: number;
  kg_donated: number;
  cost_kzt_per_kg: number;
  updated_at: string;
}

export interface EcoRecommendation {
  title: string;
  detail: string;
}

export interface EcoRecommendations {
  generated_at: string;
  provider: 'google-gemini' | 'offline-fallback';
  model: string | null;
  /** Числа, которые модели разрешили использовать. Рекомендации сверяются
   *  с ними на бэкенде, а поле возвращается, чтобы проверку можно было
   *  повторить руками. */
  facts: Record<string, unknown>;
  recommendations: EcoRecommendation[];
}

export interface FastAPIValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorDetail {
  detail: string | FastAPIValidationError[];
}
