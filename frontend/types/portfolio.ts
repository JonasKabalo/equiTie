// Mirrors the backend's /api JSON shapes.

export interface InvestorSummary {
  investor_id: string
  investor_name: string
  investor_type: string
  reporting_currency: string
  tech_savviness: string | null
  kyc_status: string
  num_deals: number
}

export interface HoldingRound {
  round: string
  deal_id: string
  deal_currency: string
  effective_share_price: number
  entry_share_price: number
  latest_share_price: number
  units: number
  current_value_reporting: number
  contributed_reporting: number
  net_distributions_reporting: number
  moic: number | null
}

export interface CompanyHolding {
  company_id: string
  company_name: string
  sector: string
  company_status: string
  current_value: number
  contributed: number
  commitment: number
  net_distributions: number
  moic: number | null
  rounds: HoldingRound[]
}

export interface PendingCommitment {
  company_id: string
  company_name: string
  deal_id: string
  round: string
  outstanding_commitment: number
  deal_currency: string
  outstanding_reporting: number
}

export interface SectorWeight {
  sector: string
  contributed: number
  count: number
}

export interface PortfolioSignals {
  tech_savviness: string | null
  age: number | null
  investor_type: string
  kyc_status: string
  onboarded_date: string | null
  num_deals: number
  num_companies: number
  top_sectors: string[]
  top_holding: string | null
  concentration_pct: number | null
}

export interface Portfolio {
  investor_id: string
  investor_name: string
  reporting_currency: string
  has_holdings: boolean
  total_committed: number
  total_contributed: number
  total_current_value: number
  total_net_distributions: number
  total_gross_distributions: number
  portfolio_moic: number | null
  dpi: number | null
  rvpi: number | null
  num_deals: number
  num_companies: number
  holdings: CompanyHolding[]
  pending_commitments: PendingCommitment[]
  top_sectors: SectorWeight[]
  signals: PortfolioSignals
}

export interface Citation {
  source: string
  row_id: string
}
