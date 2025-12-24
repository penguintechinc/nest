/**
 * Resource list component
 * Displays resources in tabbed view with color coding by lifecycle
 */

import React, { useState, useEffect } from 'react';
import { Resource, LifecycleMode } from '../../types/resource';
import ResourceCard from './ResourceCard';
import resourceService from '../../services/resources';
import { lifecycleColors } from '../../theme/lifecycleColors';

interface ResourceListProps {
  onSelectResource?: (resource: Resource) => void;
  compact?: boolean;
}

const ResourceList: React.FC<ResourceListProps> = ({ onSelectResource, compact = false }) => {
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | LifecycleMode>('all');

  useEffect(() => {
    fetchResources();
  }, []);

  const fetchResources = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await resourceService.getResources();
      setResources(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch resources');
    } finally {
      setLoading(false);
    }
  };

  const filterResourcesByLifecycle = (lifecycle: LifecycleMode) => {
    return resources.filter((r) => r.lifecycle_mode === lifecycle);
  };

  const tabs = [
    { key: 'all' as const, label: 'All Resources', count: resources.length },
    {
      key: LifecycleMode.FULL as const,
      label: lifecycleColors.full.label,
      count: filterResourcesByLifecycle(LifecycleMode.FULL).length,
      color: lifecycleColors.full.primary,
    },
    {
      key: LifecycleMode.PARTIAL as const,
      label: lifecycleColors.partial.label,
      count: filterResourcesByLifecycle(LifecycleMode.PARTIAL).length,
      color: lifecycleColors.partial.primary,
    },
    {
      key: LifecycleMode.MONITOR_ONLY as const,
      label: lifecycleColors.monitor_only.label,
      count: filterResourcesByLifecycle(LifecycleMode.MONITOR_ONLY).length,
      color: lifecycleColors.monitor_only.primary,
    },
  ];

  const displayedResources =
    activeTab === 'all' ? resources : filterResourcesByLifecycle(activeTab);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
        <button
          onClick={fetchResources}
          className="ml-4 underline hover:no-underline font-medium"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <div className="flex flex-wrap gap-1 -mb-px">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 font-medium text-sm border-b-2 transition ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
              style={
                activeTab === tab.key && 'color' in tab
                  ? { borderBottomColor: tab.color as string }
                  : {}
              }
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>
      </div>

      {/* Empty State */}
      {displayedResources.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-4">No resources found</p>
          <button
            onClick={fetchResources}
            className="text-blue-600 hover:text-blue-700 font-medium underline"
          >
            Refresh
          </button>
        </div>
      )}

      {/* Resource Grid */}
      {displayedResources.length > 0 && (
        <div
          className={
            compact
              ? 'space-y-2'
              : 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
          }
        >
          {displayedResources.map((resource) => (
            <ResourceCard
              key={resource.id}
              resource={resource}
              onClick={onSelectResource}
              compact={compact}
            />
          ))}
        </div>
      )}

      {/* Refresh Button */}
      <div className="flex justify-end pt-4">
        <button
          onClick={fetchResources}
          className="text-sm text-gray-600 hover:text-gray-900 underline"
        >
          Refresh
        </button>
      </div>
    </div>
  );
};

export default ResourceList;
