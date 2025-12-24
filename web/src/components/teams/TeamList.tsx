/**
 * Team list component
 * Displays teams and their members
 */

import React, { useState, useEffect } from 'react';
import { Team } from '../../types/team';

interface TeamListProps {
  onSelectTeam?: (team: Team) => void;
}

const TeamList: React.FC<TeamListProps> = ({ onSelectTeam }) => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      // TODO: Implement API call to fetch teams
      // const result = await teamService.getTeams();
      // setTeams(result.items);

      // Placeholder data for now
      setTeams([
        {
          id: '1',
          name: 'DevOps Team',
          description: 'Infrastructure and operations team',
          members_count: 5,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: '2',
          name: 'Security Team',
          description: 'Security and compliance team',
          members_count: 3,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch teams');
    } finally {
      setLoading(false);
    }
  };

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
          onClick={fetchTeams}
          className="ml-4 underline hover:no-underline font-medium"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {teams.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-4">No teams found</p>
          <button
            onClick={fetchTeams}
            className="text-blue-600 hover:text-blue-700 font-medium underline"
          >
            Refresh
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {teams.map((team) => (
            <div
              key={team.id}
              className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition cursor-pointer border border-gray-200"
              onClick={() => onSelectTeam?.(team)}
            >
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">{team.name}</h3>
                <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
                  {team.members_count} members
                </span>
              </div>

              {team.description && (
                <p className="text-gray-600 text-sm mb-4">{team.description}</p>
              )}

              <div className="text-xs text-gray-500 space-y-1">
                <p>Created: {new Date(team.created_at).toLocaleDateString()}</p>
                <p>Updated: {new Date(team.updated_at).toLocaleDateString()}</p>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-100">
                <button className="text-sm font-medium text-blue-600 hover:text-blue-700">
                  View Details →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TeamList;
