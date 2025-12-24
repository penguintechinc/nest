export interface Team {
  id: string;
  name: string;
  description?: string;
  members_count: number;
  created_at: string;
  updated_at: string;
}

export interface TeamMember {
  id: string;
  team_id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  role: 'admin' | 'member' | 'viewer';
  joined_at: string;
}

export interface CreateTeamInput {
  name: string;
  description?: string;
}
