import { describe, expect, it } from 'vitest';
import { extractWorkflowTaskInput } from './workflowInvocation';

describe('extractWorkflowTaskInput', () => {
  const name = '需求评审流程';

  it('returns the trimmed message when the workflow name is absent', () => {
    expect(extractWorkflowTaskInput('  只是普通的问题  ', name)).toBe('只是普通的问题');
  });

  it('drops a pure invocation phrase before the workflow name', () => {
    expect(extractWorkflowTaskInput(`请帮我调用本项目${name}：评审登录模块`, name)).toBe('评审登录模块');
  });

  it('keeps task wording that appears before the workflow name', () => {
    expect(extractWorkflowTaskInput(`评审支付接口，使用${name}`, name)).toBe('评审支付接口，使用');
  });

  it('removes a trailing invocation clause and joins both sides of the name', () => {
    expect(extractWorkflowTaskInput(`整理发布清单，调用工作流 ${name} 并给出风险`, name)).toBe(
      '整理发布清单\n并给出风险',
    );
  });

  it('falls back to the whole message when only the name and invocation remain', () => {
    expect(extractWorkflowTaskInput(`运行${name}`, name)).toBe(`运行${name}`);
  });
});
