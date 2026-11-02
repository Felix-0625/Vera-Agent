import React from 'react';
import { SettingsSkillsTabProps } from './SettingsSkillsTabParts';
import { SettingsSkillsTabView } from './SettingsSkillsTabView';
import { useSettingsSkillsTab } from './useSettingsSkillsTab';
export const SettingsSkillsTab: React.FC<SettingsSkillsTabProps> = (props) => {
  const view = useSettingsSkillsTab(props);
  return <SettingsSkillsTabView {...view} />;
};
