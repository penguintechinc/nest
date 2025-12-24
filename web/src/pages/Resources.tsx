/**
 * Resources page
 * Full resource management interface
 */

import React, { useState } from 'react';
import ResourceList from '../components/resources/ResourceList';
import ResourceWizard from '../components/resources/ResourceWizard';
import { Resource } from '../types/resource';

const Resources: React.FC = () => {
  const [showWizard, setShowWizard] = useState(false);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(null);

  const handleResourceCreated = () => {
    setShowWizard(false);
    // Optionally refresh the list here
  };

  if (showWizard) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Create Resource</h1>
          <p className="text-gray-600 mt-2">Add a new cloud resource to NEST</p>
        </div>
        <ResourceWizard onSuccess={handleResourceCreated} onCancel={() => setShowWizard(false)} />
      </div>
    );
  }

  if (selectedResource) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => setSelectedResource(null)}
          className="text-blue-600 hover:text-blue-700 font-medium"
        >
          ← Back to Resources
        </button>

        <div>
          <h1 className="text-3xl font-bold text-gray-900">{selectedResource.name}</h1>
          <p className="text-gray-600 mt-2">{selectedResource.type}</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Resource Details */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Details</h2>
            <dl className="space-y-4">
              <div>
                <dt className="text-sm font-medium text-gray-600">Status</dt>
                <dd className="text-lg text-gray-900 capitalize">{selectedResource.status}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-600">Cloud Provider</dt>
                <dd className="text-lg text-gray-900">{selectedResource.cloud_provider}</dd>
              </div>
              {selectedResource.region && (
                <div>
                  <dt className="text-sm font-medium text-gray-600">Region</dt>
                  <dd className="text-lg text-gray-900">{selectedResource.region}</dd>
                </div>
              )}
              <div>
                <dt className="text-sm font-medium text-gray-600">Created</dt>
                <dd className="text-lg text-gray-900">
                  {new Date(selectedResource.created_at).toLocaleDateString()}
                </dd>
              </div>
            </dl>
          </div>

          {/* Actions */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
            <div className="space-y-2">
              <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
                Edit Resource
              </button>
              <button className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 transition font-medium">
                View Metrics
              </button>
              <button className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 transition font-medium">
                View Logs
              </button>
              <button className="w-full px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition font-medium">
                Delete Resource
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Resources</h1>
          <p className="text-gray-600 mt-2">Manage your cloud resources</p>
        </div>
        <button
          onClick={() => setShowWizard(true)}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
        >
          + Create Resource
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <ResourceList onSelectResource={setSelectedResource} />
      </div>
    </div>
  );
};

export default Resources;
