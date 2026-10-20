---
name: hermes-wave-implementation
description: Create Wave 1 UI panels for Hermes Agent desktop (Now Boarding, Crew Queue, Alerts Deck, Mission Control, Ship Log, Focus Mode)
version: 0.1.0
author: Hermes Agent, Nous Research
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ui, panels, hermes-agent, desktop, wave1]
    related_skills: [hermes-agent-skill-authoring]
---

# Hermes Wave Implementation Skill

Create Wave 1 user interface panels for the Hermes Agent desktop application, following the Hermes design system conventions (flat, not boxed; token-based styling; Tabler icons; shadow elevation).

## When to Use

- User requests implementation of Hermes Agent Wave 1 panels: Now Boarding, Crew Queue, Alerts Deck, Mission Control, Ship Log, or Focus Mode
- Building or extending the Hermes Agent dashboard/bridge interface
- Adding new panel types that follow the established Wave 1 patterns

### Don't use for:
- Creating personal skills in `~/.hermes/skills/` (use skill_manage directly)
- Panel types outside the Wave 1 framework (those are new skills)
- Fixing unrelated Hermes issues

## Prerequisites

- Hermes Agent desktop app (`apps/desktop/` in the hermes-agent repo)
- Familiarity with the Hermes design system (see `DESIGN.md`)
- Tabler Icons (`tabler-icons-react`)
- Hermes UI primitives: `Button`, `Card`, `Table`, `Loader`, `Tabs`, `ScrollArea`
- API endpoints: `/api/hermes/urgent-tasks`, `/api/hermes/agent-states`, `/api/hermes/alerts-deck`, `/api/hermes/focus-state`, `/api/hermes/ship-log`

## How to Run

### Create a New Wave 1 Panel

1. **Create the panel component** under `apps/desktop/src/components/wave-1-panels/<panel-name>.tsx`
   - Import Hermes UI primitives from `../ui/`
   - Fetch data from the appropriate `/api/hermes/*` endpoint
   - Include loading, empty, and error states
   - Follow the flat design: no nested boxes, use `--ui-*` CSS variables
   - Use Tabler icons for all visual elements

2. **Add the panel to the index**
   - Export from `wave-1-panels/index.tsx`
   - Register in the Hermes desktop sidebar/router if needed

3. **Test the panel**
   - Verify loading states work
   - Verify empty states render correctly
   - Verify error toast notifications

### Example: Now Boarding Panel

```typescript
import { TablerIcon } from "tabler-icons-react";
import { Button } from "../ui/button";
import { useToast } from "../store/toast";

export const NowBoardingPanel = () => {
  const { toast } = useToast();
  const [tasks, setTasks] = useState<UrgentTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUrgentTasks = async () => {
      setLoading(true);
      try {
        const response = await fetch("/api/hermes/urgent-tasks?limit=3");
        const data = await response.json();
        setTasks(data.tasks || []);
      } catch (error) {
        toast({ title: "Error", description: "Failed to fetch urgent tasks", variant: "destructive" });
      } finally {
        setLoading(false);
      }
    };

    fetchUrgentTasks();
    const interval = setInterval(fetchUrgentTasks, 120_000); // 2-minute refresh
    return () => clearInterval(interval);
  }, [toast]);

  if (loading) {
    return (<div className="flex h-20 items-center justify-center text-muted-foreground"><Loader size={20} /></div>);
  }

  if (tasks.length === 0) {
    return (<div className="flex h-20 items-center justify-center text-muted-foreground"><TablerIcon name="check-circle" size={20} className="opacity-50" /><span className="ml-2">No urgent tasks</span></div>);
  }

  return (
    <div className="space-y-2">
      {tasks.map((task, index) => (
        <div key={task.id} className="flex items-center gap-3 px-3 py-2 rounded-md background-nous-subtle hover:bg-nous-hover transition-colors">
          <span className="urgency-badge">{index + 1}</span>
          <TablerIcon name={task.priorityIcon} size={16} className="priority-icon" />
          <div className="flex-1 min-w-0">
            <p className="font-medium line-clamp-1">{task.title}</p>
            <p className="text-xs text-muted-foreground line-clamp-1">Deadline: {task.deadline} - Agent: {task.agent}</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => jumpToTask(task.id)} className="flex items-center gap-1">
            Jump
          </Button>
        </div>
      ))}
    </div>
  );
};

interface UrgentTask {
  id: string;
  title: string;
  priority: "critical" | "high" | "medium";
  deadline: string;
  agent: string;
  estimatedMinutes: number;
  urgencyScore: number;
  priorityIcon: "exclamation-triangle" | "alert-circle" | "info";
}
```

## Pitfalls

1. **Using raw colors/literals instead of tokens** - Always reference `--ui-*` CSS variables
2. **Nested box borders** - Hermes uses flat design; group with whitespace, not dividers
3. **Missing loading/error states** - Always include spinner/toast for failed fetches
4. **Wrong refresh intervals** - Match the panel type: Now Boarding (2min), Crew Queue (15s), Alerts Deck (30s), Ship Log (20s), Focus Mode (10s)
5. **Using `•` (bullet) character in JSX** - Use text alternatives or safe HTML

## Verification

- Panel renders without errors
- Data fetches from Hermes API endpoint
- Loading spinner shows during fetch
- Empty state shows when no data
- Error toast appears on fetch failure
- Design system tokens used (not raw literals)
- Tabler icons used for all visual elements
- Refresh interval matches panel type

## Related Skills

- `hermes-agent-skill-authoring` - Author in-repo SKILL.md files
- `plan` - Write implementation plans to `.hermes/plans/`
- `simplify-code` - Parallel cleanup of code changes

---
