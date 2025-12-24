/**
 * Lifecycle badge component
 * CRITICAL UX: Color-coded badge showing resource lifecycle mode
 * Displays icon and text label for lifecycle classification
 */

import React from 'react';
import { LifecycleMode } from '../../types/resource';
import { lifecycleColors } from '../../theme/lifecycleColors';

interface LifecycleBadgeProps {
  mode: LifecycleMode;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'badge' | 'pill' | 'detailed';
}

const iconMap: Record<string, string> = {
  CloudQueue: '☁️',
  Link: '🔗',
  Visibility: '👁️',
};

const LifecycleBadge: React.FC<LifecycleBadgeProps> = ({
  mode,
  size = 'md',
  variant = 'badge',
}) => {
  const color = lifecycleColors[mode];
  const icon = iconMap[color.icon] || '•';

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  const baseClasses = `inline-flex items-center space-x-1 rounded-full font-medium transition-colors ${sizeClasses[size]}`;

  if (variant === 'pill') {
    return (
      <div
        className={baseClasses}
        style={{
          backgroundColor: color.light,
          color: color.primary,
          border: `1px solid ${color.primary}`,
        }}
      >
        <span>{icon}</span>
        <span>{color.label}</span>
      </div>
    );
  }

  if (variant === 'detailed') {
    return (
      <div
        className={`${baseClasses} flex-col items-start`}
        style={{
          backgroundColor: color.light,
          color: color.primary,
          border: `1px solid ${color.primary}`,
        }}
      >
        <div className="flex items-center space-x-1">
          <span>{icon}</span>
          <span className="font-semibold">{color.label}</span>
        </div>
        <p className="text-xs opacity-75 mt-1">{color.description}</p>
      </div>
    );
  }

  // Default badge variant
  return (
    <div
      className={baseClasses}
      style={{
        backgroundColor: color.background,
        color: color.primary,
      }}
    >
      <span className="text-lg">{icon}</span>
      <span>{color.label}</span>
    </div>
  );
};

export default LifecycleBadge;
