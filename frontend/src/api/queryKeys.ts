export const queryKeys = {
  user: {
    profile: (userId: string | number | undefined) => ['userProfile', userId] as const,
    dashboard: (userId: string | number | undefined) => ['userDashboard', userId] as const,
    transactions: (userId: string | number | undefined) => ['userTransactions', userId] as const,
    nfts: (userId: string | number | undefined) => ['userNfts', userId] as const,
  },
  leaderboard: ['leaderboard'] as const,
  containers: (activeOnly: boolean) => ['containers', activeOnly] as const,
  shop: {
    items: ['shopItems'] as const,
  },
  volunteer: {
    tasks: (includeCompleted: boolean) => ['volunteerTasks', includeCompleted] as const,
  },
  community: {
    messages: (limit: number) => ['communityMessages', limit] as const,
  },
  eco: {
    savings: (days: number) => ['ecoSavings', days] as const,
    revenue: (days: number, projection: number | undefined) =>
      ['ecoRevenue', days, projection] as const,
    forecast: ['ecoForecast'] as const,
    route: (horizonHours: number) => ['ecoRoute', horizonHours] as const,
    recommendations: (days: number) => ['ecoRecommendations', days] as const,
    businessForecast: (target: string | undefined, weeks: number) =>
      ['ecoBusinessForecast', target, weeks] as const,
    profile: ['ecoProfile'] as const,
    writeOffs: (limit: number) => ['ecoWriteOffs', limit] as const,
  },
  dispatcher: {
    summary: ['dispatcherSummary'] as const,
    briefing: ['dispatcherBriefing'] as const,
    commands: (deviceId?: string, status?: string, limit = 50) => ['dispatcherCommands', deviceId, status, limit] as const,
    deviceStatuses: ['dispatcherDeviceStatuses'] as const,
    cameraAnalysis: (deviceId?: string) => ['dispatcherCameraAnalysis', deviceId] as const,
  }
};
