import { SkillItem } from '../../types/settings';
export interface SettingsSkillsTabProps {
  skills: SkillItem[];
  onDelete: (name: string) => Promise<void>;
  onNewSkill?: () => void;
}
