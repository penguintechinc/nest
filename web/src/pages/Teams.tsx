/**
 * Teams page
 * Team management interface
 */

import React from 'react';
import TeamList from '../components/teams/TeamList';
import { Team } from '../types/team';

const Teams: React.FC = () => {
  const [selectedTeam, setSelectedTeam] = React.useState<Team | null>(null);

  if (selectedTeam) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => setSelectedTeam(null)}
          className="text-blue-600 hover:text-blue-700 font-medium"
        >
          ← Back to Teams
        </button>

        <div>
          <h1 className="text-3xl font-bold text-gray-900">{selectedTeam.name}</h1>
          {selectedTeam.description && (
            <p className="text-gray-600 mt-2">{selectedTeam.description}</p>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Members</h3>
            <p className="text-3xl font-bold text-blue-600">{selectedTeam.members_count}</p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Created</h3>
            <p className="text-lg text-gray-900">
              {new Date(selectedTeam.created_at).toLocaleDateString()}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Updated</h3>
            <p className="text-lg text-gray-900">
              {new Date(selectedTeam.updated_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Team Actions</h2>
          <div className="space-y-2">
            <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
              Manage Members
            </button>
            <button className="w-full px-4 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 transition font-medium">
              Edit Team
            </button>
            <button className="w-full px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition font-medium">
              Delete Team
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Teams</h1>
          <p className="text-gray-600 mt-2">Manage team access and permissions</p>
        </div>
        <button className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
          + Create Team
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <TeamList onSelectTeam={setSelectedTeam} />
      </div>
    </div>
  );
};

export default Teams;
