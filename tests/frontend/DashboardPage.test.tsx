import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { DashboardPage } from "../../frontend/src/pages/DashboardPage";
import * as metricsApi from "../../frontend/src/api/metrics";
import * as contractsApi from "../../frontend/src/api/contracts";
import { ApiError } from "../../frontend/src/api/client";

function stubAllMetrics() {
  vi.spyOn(metricsApi, "getSummary").mockResolvedValue({
    period_start: "2025-09-08",
    period_end: "2026-09-08",
    total_value: 510942495.35,
    contract_count: 112,
    accenture_value: 12000000,
    accenture_share: 0.024,
    total_value_delta_pct: -46,
    contract_count_delta_pct: -3.4,
    accenture_value_delta_pct: null,
  });
  vi.spyOn(metricsApi, "getShareOverTime").mockResolvedValue({ granularity: "quarter", points: [] });
  vi.spyOn(metricsApi, "getByTheme").mockResolvedValue([]);
  vi.spyOn(metricsApi, "getCompetitorMomentum").mockResolvedValue([]);
  vi.spyOn(metricsApi, "getExpiring").mockResolvedValue([]);
  vi.spyOn(metricsApi, "getByAgency").mockResolvedValue([]);
  vi.spyOn(metricsApi, "getServiceOfferings").mockResolvedValue([]);
  vi.spyOn(metricsApi, "getAddressableSummary").mockResolvedValue({
    fy_window: "last5",
    total_defence_value: 1000,
    addressable_value: 100,
    addressable_annualised: 60,
    addressable_count: 5,
    addressable_pct_of_defence: 0.1,
    accenture_value: 10,
    accenture_share_of_addressable: 0.1,
  });
  vi.spyOn(metricsApi, "getGrowth").mockResolvedValue({
    service_offering: null,
    points: [],
    cagr_pct: null,
    latest_fy_value: 0,
    peak_fy_label: null,
  });
  vi.spyOn(metricsApi, "getNetwork").mockResolvedValue({ basis: "all-defence", nodes: [], edges: [] });
  vi.spyOn(metricsApi, "getNetworkContracts").mockResolvedValue({ total: 0, limit: 500, items: [] });
  vi.spyOn(metricsApi, "getPeerComparison").mockResolvedValue({
    cohort: "big4",
    cohort_label: "Big 4",
    basis: "addressable",
    accenture_value: 55,
    accenture_count: 3,
    cohort_value: 134,
    cohort_count: 20,
    accenture_share: 0.29,
    members: [],
    series: [],
  });
  vi.spyOn(contractsApi, "getFilters").mockResolvedValue({
    themes: [{ slug: "workforce", label: "Workforce" }],
    competitors: [{ slug: "accenture", label: "Accenture", category: "accenture" }],
    agencies: [],
    value_range: { min: 0, max: 1 },
    date_range: { min: null, max: null },
  });
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the positioning and peer sections once metrics resolve", async () => {
    stubAllMetrics();
    render(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByText(/Accenture's Current Positioning/i)).toBeInTheDocument(),
    );
    expect(screen.getAllByText(/Addressable Market/i).length).toBeGreaterThan(0);
    // addressable_pct_of_defence 0.1 -> 10.0%
    expect(screen.getAllByText("10.0%").length).toBeGreaterThan(0);
    expect(screen.getByText("Accenture vs Big 4")).toBeInTheDocument();
    expect(screen.getByText("Accenture vs MBB")).toBeInTheDocument();
  });

  it("stays rendered when an addressable metric call fails", async () => {
    stubAllMetrics();
    vi.spyOn(metricsApi, "getAddressableSummary").mockRejectedValue(new ApiError("boom", 500));
    render(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByText(/Accenture's Current Positioning/i)).toBeInTheDocument(),
    );
    expect(screen.getByText("Accenture vs Challengers")).toBeInTheDocument();
  });
});
