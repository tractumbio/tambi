import { apiGet, type QueryParams } from "./client";
import type {
  AddressableSummary,
  AgencyBreakdownRow,
  CommonFilterParams,
  CompetitorMomentumRow,
  ExpiringContract,
  FyWindow,
  GrowthResponse,
  NetworkContracts,
  NetworkGraphData,
  PeerCohort,
  PeerComparison,
  ServiceOfferingRow,
  ShareOverTime,
  SummaryKpis,
  ThemeBreakdownRow,
} from "../types";

function asParams(f?: CommonFilterParams): QueryParams {
  return { ...f } as QueryParams;
}

export function getSummary(f?: CommonFilterParams): Promise<SummaryKpis> {
  return apiGet<SummaryKpis>("/metrics/summary", asParams(f));
}

export function getShareOverTime(
  granularity: "month" | "quarter" = "quarter",
  f?: CommonFilterParams,
): Promise<ShareOverTime> {
  return apiGet<ShareOverTime>("/metrics/share-over-time", { ...asParams(f), granularity });
}

export function getByTheme(f?: CommonFilterParams): Promise<ThemeBreakdownRow[]> {
  return apiGet<ThemeBreakdownRow[]>("/metrics/by-theme", asParams(f));
}

export function getCompetitorMomentum(f?: CommonFilterParams): Promise<CompetitorMomentumRow[]> {
  return apiGet<CompetitorMomentumRow[]>("/metrics/competitor-momentum", asParams(f));
}

export function getExpiring(
  withinDays = 365,
  f?: CommonFilterParams,
): Promise<ExpiringContract[]> {
  return apiGet<ExpiringContract[]>("/metrics/expiring", {
    ...asParams(f),
    within_days: withinDays,
  });
}

export function getByAgency(limit = 12, f?: CommonFilterParams): Promise<AgencyBreakdownRow[]> {
  return apiGet<AgencyBreakdownRow[]>("/metrics/by-agency", { ...asParams(f), limit });
}

export function getServiceOfferings(
  fyWindow: FyWindow = "all",
  f?: CommonFilterParams,
): Promise<ServiceOfferingRow[]> {
  return apiGet<ServiceOfferingRow[]>("/metrics/service-offerings", {
    ...asParams(f),
    fy_window: fyWindow,
  });
}

export function getAddressableSummary(
  fyWindow: FyWindow = "all",
  f?: CommonFilterParams,
): Promise<AddressableSummary> {
  return apiGet<AddressableSummary>("/metrics/addressable-summary", {
    ...asParams(f),
    fy_window: fyWindow,
  });
}

export function getGrowth(offering?: string, f?: CommonFilterParams): Promise<GrowthResponse> {
  return apiGet<GrowthResponse>("/metrics/growth", { ...asParams(f), offering });
}

export function getPeerComparison(
  cohort: PeerCohort,
  addressableOnly = true,
  f?: CommonFilterParams,
): Promise<PeerComparison> {
  return apiGet<PeerComparison>("/metrics/peer-comparison", {
    ...asParams(f),
    cohort,
    addressable_only: addressableOnly,
  });
}

export function getNetwork(
  immediateOnly = true,
  agencyLimit = 14,
  f?: CommonFilterParams,
): Promise<NetworkGraphData> {
  return apiGet<NetworkGraphData>("/metrics/network", {
    ...asParams(f),
    immediate_only: immediateOnly,
    agency_limit: agencyLimit,
  });
}

export function getNetworkContracts(
  immediateOnly = true,
  limit = 500,
  f?: CommonFilterParams,
): Promise<NetworkContracts> {
  return apiGet<NetworkContracts>("/metrics/network/contracts", {
    ...asParams(f),
    immediate_only: immediateOnly,
    limit,
  });
}
