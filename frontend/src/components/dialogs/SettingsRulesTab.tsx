import React from 'react';
import { SettingsRulesTabView } from './SettingsRulesTabView';
import { useSettingsRulesTab } from './useSettingsRulesTab';
export const SettingsRulesTab: React.FC = () => {
  const view = useSettingsRulesTab();
  return <SettingsRulesTabView {...view} />;
};
