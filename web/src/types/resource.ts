export enum LifecycleMode {
  FULL = 'full',
  PARTIAL = 'partial',
  MONITOR_ONLY = 'monitor_only',
}

export interface Resource {
  id: string;
  name: string;
  type: string;
  lifecycle_mode: LifecycleMode;
  status: 'active' | 'inactive' | 'error';
  cloud_provider: string;
  region?: string;
  tags?: Record<string, string>;
  created_at: string;
  updated_at: string;
  capabilities?: string[];
}

export interface ResourceList {
  items: Resource[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreateResourceInput {
  name: string;
  type: string;
  lifecycle_mode: LifecycleMode;
  cloud_provider: string;
  region?: string;
  tags?: Record<string, string>;
}
