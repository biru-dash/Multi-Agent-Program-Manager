import { MIAOutput, REAOutput, AgentState } from '@/types/agent';

export const mockMIAOutput: MIAOutput = {
  summary: `# Sprint Planning Meeting - Q4 2025

## Overview
The team gathered to discuss priorities for the upcoming sprint, focusing on the multi-agent accelerator platform. Key emphasis was placed on user experience improvements and backend stability.

## Context
This is the first sprint of the new accelerator project. The team has completed initial research and is ready to begin implementation.`,
  decisions: [
    'Prioritize MIA and REA agents for Sprint 1',
    'Use React + Tailwind for frontend',
    'Implement local JSON storage before cloud migration',
    'Focus on workflow visualization as primary feature',
  ],
  actions: [
    'Design workflow canvas component (Owner: Frontend Team)',
    'Implement file upload functionality (Owner: Backend Team)',
    'Create configuration panel UI (Owner: Design Team)',
    'Set up Docker environment (Owner: DevOps)',
  ],
  risks: [
    'Timeline constraints for workflow visualization',
    'Complexity of agent state management',
    'File parsing library dependencies',
  ],
  owners: [
    'Frontend Team - UI Components',
    'Backend Team - Agent Logic',
    'Design Team - UX/UI Design',
    'DevOps - Infrastructure',
  ],
};

export const mockREAOutput: REAOutput = {
  userStories: [
    {
      id: 'US-001',
      title: 'File Upload for Transcripts',
      description:
        'As a program manager, I want to upload meeting transcripts in multiple formats (PDF, DOCX, TXT) so that the MIA agent can process them for insights.',
      acceptanceCriteria: [
        'Support PDF, DOCX, and TXT file formats',
        'Drag-and-drop interface available',
        'File validation with size limits (10MB max)',
        'Visual feedback during upload',
      ],
      priority: 'high',
    },
    {
      id: 'US-002',
      title: 'Workflow Visualization',
      description:
        'As a user, I want to see a visual representation of the agent workflow so that I understand how data flows from MIA to REA.',
      acceptanceCriteria: [
        'Node-graph view with agent nodes',
        'Animated connections between agents',
        'Status indicators for each agent',
        'Real-time progress updates',
      ],
      priority: 'high',
    },
    {
      id: 'US-003',
      title: 'MIA Output Display',
      description:
        'As a user, I want to view the MIA outputs (summary, decisions, actions, risks) in an organized panel so that I can review the meeting intelligence.',
      acceptanceCriteria: [
        'Separate sections for each output type',
        'Editable Markdown support',
        'Export to JSON/Markdown',
        'Clear visual hierarchy',
      ],
      priority: 'high',
    },
    {
      id: 'US-004',
      title: 'REA User Story Generation',
      description:
        'As a product owner, I want REA to generate structured user stories from MIA outputs so that I can immediately start sprint planning.',
      acceptanceCriteria: [
        'User stories follow standard format (As a... I want... So that...)',
        'Acceptance criteria automatically generated',
        'Priority levels assigned',
        'Stories can be edited before export',
      ],
      priority: 'medium',
    },
    {
      id: 'US-005',
      title: 'Configuration Panel',
      description:
        'As an admin, I want to configure LLM parameters and output formats so that I can customize agent behavior for different use cases.',
      acceptanceCriteria: [
        'LLM model selection dropdown',
        'Confidence threshold slider (0-100%)',
        'Output format selector (JSON/Markdown/CSV)',
        'Settings persist across sessions',
      ],
      priority: 'medium',
    },
  ],
  priorities: [
    'File upload and parsing (Sprint 1)',
    'Workflow visualization (Sprint 1)',
    'MIA/REA output display (Sprint 1)',
    'Configuration panel (Sprint 2)',
    'Export functionality (Sprint 2)',
  ],
};

export const mockAgentStates: AgentState[] = [
  {
    id: 'mia',
    name: 'Meeting Intelligence Agent',
    status: 'idle',
    progress: 0,
  },
  {
    id: 'rea',
    name: 'Requirement Extraction Agent',
    status: 'idle',
    progress: 0,
  },
];

export const mockDirectREAOutput: REAOutput = {
  userStories: [
    {
      id: 'US-101',
      title: 'Independent REA Processing',
      description:
        'As a user, I want REA to process files independently so that I can extract requirements without running the full MIA pipeline.',
      acceptanceCriteria: [
        'REA accepts direct file uploads (PDF, DOCX, TXT)',
        'Processing works without MIA output',
        'User stories generated with same quality',
        'Workflow mode selector available in UI',
      ],
      priority: 'high',
    },
    {
      id: 'US-102',
      title: 'Flexible Workflow Selection',
      description:
        'As a user, I want to choose between full pipeline and direct REA modes so that I can optimize for my specific use case.',
      acceptanceCriteria: [
        'Radio button selector for workflow mode',
        'Visual representation of selected workflow',
        'Mode persists during session',
        'Clear descriptions of each mode',
      ],
      priority: 'medium',
    },
    {
      id: 'US-103',
      title: 'Direct File Analysis',
      description:
        'As a product owner, I want to upload requirement documents directly to REA so that I can skip meeting analysis when I already have structured input.',
      acceptanceCriteria: [
        'Upload interface shows relevant mode',
        'File validation works in both modes',
        'Processing time optimized for direct mode',
        'Output format consistent across modes',
      ],
      priority: 'high',
    },
  ],
  priorities: [
    'Independent REA processing (Sprint 1)',
    'Workflow mode selection (Sprint 1)',
    'Direct file analysis optimization (Sprint 2)',
  ],
};
