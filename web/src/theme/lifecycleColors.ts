/**
 * CRITICAL UX: Lifecycle color scheme for resource management
 * These colors are essential for visual differentiation of resource lifecycle modes
 */

export const lifecycleColors = {
  full: {
    primary: '#1976d2',      // Blue
    light: '#e3f2fd',
    background: '#bbdefb',
    icon: 'CloudQueue',
    label: 'Fully Managed',
    description: 'NEST manages the complete lifecycle of this resource',
  },
  partial: {
    primary: '#f57c00',      // Orange
    light: '#fff3e0',
    background: '#ffe0b2',
    icon: 'Link',
    label: 'Externally Managed',
    description: 'This resource is managed externally, NEST provides monitoring',
  },
  monitor_only: {
    primary: '#757575',      // Gray
    light: '#f5f5f5',
    background: '#e0e0e0',
    icon: 'Visibility',
    label: 'Monitor Only',
    description: 'NEST monitors this resource for awareness and alerting',
  },
};

export const getLifecycleColor = (mode: 'full' | 'partial' | 'monitor_only') => {
  return lifecycleColors[mode];
};

export const lifecycleModeLabels = {
  full: 'Fully Managed',
  partial: 'Externally Managed',
  monitor_only: 'Monitor Only',
};
