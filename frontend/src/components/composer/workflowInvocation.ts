const invocationIntro = '(?:(?:请帮我|请|麻烦|帮我)\\s*)?';
const invocationVerb = '(?:调用|运行|执行|启动|使用|用)';
const invocationScope = '(?:(?:本项目|项目内|项目中的|当前项目|当前|这个|该|项目)\\s*)?';
const workflowNoun = '(?:组织架构|工作流|流程|架构)';

const invocationOnly = new RegExp(`^\\s*${invocationIntro}${invocationVerb}\\s*${invocationScope}(?:${workflowNoun})?\\s*$`);
const invocationLead = new RegExp(`^\\s*${invocationIntro}${invocationVerb}\\s*${invocationScope}${workflowNoun}\\s*`);
const invocationTail = new RegExp(`\\s*${invocationIntro}${invocationVerb}\\s*${invocationScope}${workflowNoun}\\s*$`);

function trimBoundaryPunctuation(value: string): string {
  return value.replace(/^[\s，,、：:。；;\-—]+/, '').replace(/[\s，,、：:。；;\-—]+$/, '').trim();
}

/** Extract task text around a named project workflow without deleting task wording. */
export function extractWorkflowTaskInput(message: string, workflowName: string): string {
  const nameIndex = message.indexOf(workflowName);
  if (nameIndex < 0) return message.trim();

  const rawBeforeName = message.slice(0, nameIndex);
  const beforeName = invocationOnly.test(rawBeforeName)
    ? ''
    : rawBeforeName.replace(invocationLead, '').replace(invocationTail, '');
  const afterName = message.slice(nameIndex + workflowName.length);
  const taskParts = [beforeName, afterName].map(trimBoundaryPunctuation).filter(Boolean);

  return taskParts.length ? taskParts.join('\n') : message.trim();
}
