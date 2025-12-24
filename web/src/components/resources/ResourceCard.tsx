/**
 * Resource card component
 * CRITICAL UX: Color-coded card with 4px left border matching lifecycle
 * Displays resource information with lifecycle badge
 */

import React from 'react';
import { Resource } from '../../types/resource';
import { lifecycleColors } from '../../theme/lifecycleColors';
import LifecycleBadge from './LifecycleBadge';
import CapabilityIndicators from './CapabilityIndicators';

interface ResourceCardProps {
  resource: Resource;
  onClick?: (resource: Resource) => void;
  compact?: boolean;
}

const ResourceCard: React.FC<ResourceCardProps> = ({ resource, onClick, compact = false }) => {
  const lifecycleColor = lifecycleColors[resource.lifecycle_mode];
  const statusColor = {
    active: 'green',
    inactive: 'gray',
    error: 'red',
  }[resource.status];

  if (compact) {
    return (
      <div
        className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition cursor-pointer"
        style={{
          borderLeft: `4px solid ${lifecycleColor.primary}`,
        }}
        onClick={() => onClick?.(resource)}
      >
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-gray-900 flex-1">{resource.name}</h3>
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 ml-2 mt-1`}
            style={{ backgroundColor: statusColor }}
            title={resource.status}
          ></span>
        </div>
        <div className="flex items-center justify-between">
          <div className="text-xs text-gray-600 space-y-1">
            <p>Type: {resource.type}</p>
            <p>Provider: {resource.cloud_provider}</p>
          </div>
          <LifecycleBadge mode={resource.lifecycle_mode} size="sm" />
        </div>
      </div>
    );
  }

  return (
    <div
      className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition cursor-pointer bg-white"
      style={{
        borderLeft: `4px solid ${lifecycleColor.primary}`,
      }}
      onClick={() => onClick?.(resource)}
    >
      {/* Header with status */}
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">{resource.name}</h3>
            <p className="text-sm text-gray-600 mt-1">{resource.type}</p>
          </div>
          <div className="flex items-center space-x-2">
            <span
              className={`inline-block w-3 h-3 rounded-full`}
              style={{ backgroundColor: statusColor }}
              title={`Status: ${resource.status}`}
            ></span>
            <span className="text-xs font-medium text-gray-700 capitalize">{resource.status}</span>
          </div>
        </div>

        {/* Lifecycle Badge */}
        <LifecycleBadge mode={resource.lifecycle_mode} variant="pill" />
      </div>

      {/* Body with details */}
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-600 uppercase font-semibold">Cloud Provider</p>
            <p className="text-sm text-gray-900 mt-1">{resource.cloud_provider}</p>
          </div>
          {resource.region && (
            <div>
              <p className="text-xs text-gray-600 uppercase font-semibold">Region</p>
              <p className="text-sm text-gray-900 mt-1">{resource.region}</p>
            </div>
          )}
        </div>

        {/* Tags */}
        {resource.tags && Object.keys(resource.tags).length > 0 && (
          <div>
            <p className="text-xs text-gray-600 uppercase font-semibold mb-2">Tags</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(resource.tags).map(([key, value]) => (
                <span
                  key={key}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                >
                  {key}: {value}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Timestamps */}
        <div className="text-xs text-gray-500 space-y-1">
          <p>Created: {new Date(resource.created_at).toLocaleDateString()}</p>
          <p>Updated: {new Date(resource.updated_at).toLocaleDateString()}</p>
        </div>

        {/* Capabilities */}
        <div className="border-t border-gray-100 pt-4">
          <CapabilityIndicators lifecycle_mode={resource.lifecycle_mode} compact={true} />
        </div>
      </div>

      {/* Footer action */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
        <button className="text-sm font-medium text-blue-600 hover:text-blue-700">
          View Details →
        </button>
      </div>
    </div>
  );
};

export default ResourceCard;
