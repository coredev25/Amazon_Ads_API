'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Target, Key, LayoutDashboard, Tag, ExternalLink } from 'lucide-react';
import { cn } from '@/utils/helpers';

type EntityType = 'campaign' | 'keyword' | 'ad_group' | 'targeting' | 'negative_keyword' | 'search_term';

interface EntityLinkProps {
  type: EntityType;
  name: string;
  id?: string | number;
  className?: string;
  showIcon?: boolean;
  showArrow?: boolean;
  maxWidth?: string;
}

const entityConfig: Record<EntityType, { icon: typeof Target; href: string; paramKey: string }> = {
  campaign: { icon: Target, href: '/dashboard/campaigns', paramKey: 'campaign_id' },
  keyword: { icon: Key, href: '/dashboard/keywords', paramKey: 'keyword_id' },
  ad_group: { icon: LayoutDashboard, href: '/dashboard/campaigns', paramKey: 'ad_group_id' },
  targeting: { icon: Tag, href: '/dashboard/targeting', paramKey: 'targeting_id' },
  negative_keyword: { icon: Key, href: '/dashboard/negatives', paramKey: 'nk_id' },
  search_term: { icon: Key, href: '/dashboard/keywords', paramKey: 'search_term' },
};

export default function EntityLink({
  type,
  name,
  id,
  className,
  showIcon = false,
  showArrow = false,
  maxWidth,
}: EntityLinkProps) {
  const router = useRouter();
  const config = entityConfig[type] || entityConfig.campaign;
  const Icon = config.icon;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const url = id ? `${config.href}?${config.paramKey}=${id}` : config.href;
    router.push(url);
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        'entity-link inline-flex items-center gap-1.5 text-left',
        maxWidth && 'truncate',
        className
      )}
      style={maxWidth ? { maxWidth } : undefined}
      title={name}
    >
      {showIcon && <Icon className="w-3.5 h-3.5 flex-shrink-0 opacity-50" />}
      <span className="truncate">{name}</span>
      {showArrow && <ExternalLink className="w-3 h-3 flex-shrink-0 opacity-0 group-hover:opacity-50 transition-opacity" />}
    </button>
  );
}
