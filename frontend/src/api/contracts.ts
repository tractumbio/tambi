import { apiGet, type QueryParams } from "./client";
import type { CommonFilterParams, ContractPage, FilterOptions } from "../types";

export interface ContractListParams extends CommonFilterParams {
  defence_only?: boolean;
  sort?: "value_amount" | "date_published" | "period_end";
  order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export function listContracts(params?: ContractListParams): Promise<ContractPage> {
  return apiGet<ContractPage>("/contracts", { ...params } as QueryParams);
}

export function getFilters(): Promise<FilterOptions> {
  return apiGet<FilterOptions>("/filters");
}
