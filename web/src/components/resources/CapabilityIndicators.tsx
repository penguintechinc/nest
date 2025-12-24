/**
 * Capability indicators component
 * Shows what NEST can do with each resource
 */

import React from 'react';
import { LifecycleMode } from '../../types/resource';

interface CapabilityIndicatorsProps {
  lifecycle_mode: LifecycleMode;
  compact?: boolean;
}

const capabilityMap: Record<LifecycleMode, { name: string; icon: string }[]> = {
  [LifecycleMode.FULL]: [
    { name: 'Create', icon: '✨' },
    { name: 'Read', icon: '📖' },
    { name: 'Update', icon: '✏️' },
    { name: 'Delete', icon: '🗑️' },
    { name: 'Monitor', icon: '📊' },
    { name: 'Backup', icon: '💾' },
  ],
  [LifecycleMode.PARTIAL]: [
    { name: 'Read', icon: '📖' },
    { name: 'Monitor', icon: '📊' },
    { name: 'Alert', icon: '🔔' },
  ],
  [LifecycleMode.MONITOR_ONLY]: [
    { name: 'Monitor', icon: '📊' },
    { name: 'Alert', icon: '🔔' },
    { name: 'Report', icon: '📋' },
  ],
};

const CapabilityIndicators: React.FC<CapabilityIndicatorsProps> = ({
  lifecycle_mode,
  compact = false,
}) => {
  const capabilities = capabilityMap[lifecycle_mode];

  if (compact) {
    return (
      <div className="flex items-center space-x-1 text-sm">
        {capabilities.slice(0, 3).map((cap) => (
          <span key={cap.name} title={cap.name} className="text-lg">
            {cap.icon}
          </span>
        ))}
        {capabilities.length > 3 && (
          <span className="text-gray-500">+{capabilities.length - 3}</span>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-gray-700 mb-2">NEST Capabilities</h4>
      <div className="grid grid-cols-2 gap-2">
        {capabilities.map((cap) => (
          <div
            key={cap.name}
            className="flex items-center space-x-2 px-3 py-2 bg-gray-50 rounded-md border border-gray-200"
          >
            <span className="text-lg">{cap.icon}</span>
            <span className="text-sm text-gray-700">{cap.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CapabilityIndicators;
