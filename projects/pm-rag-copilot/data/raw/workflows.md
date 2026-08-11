# Jira Documentation: Creating Custom Workflows

## What is a Jira Workflow?
A Jira workflow is a set of statuses and transitions that an issue moves through during its lifecycle—typically representing your team's business process (e.g., `To Do` -> `In Progress` -> `In Review` -> `Done`).

## How to Create a Custom Workflow
To create or customize a workflow in Jira (requires Jira Administrator permissions):
1. Navigate to **Project Settings** -> **Workflows** (or Jira Settings -> Issues -> Workflows for global workflows).
2. Click **Add Workflow** and choose **Create New** (or copy an existing default workflow).
3. Enter a **Name** (e.g., "Software Development Workflow v2") and an optional description.
4. Use the visual workflow designer to add **Statuses** and **Transitions**:
   - **Add Status**: Click **+ Add Status**, enter status name (e.g., `Code Review`), and choose a category (`To Do`, `In Progress`, or `Done`).
   - **Add Transition**: Click **+ Add Transition**, select the source status and target status, and name the transition action (e.g., `Submit for Review`).
5. Set up **Triggers, Conditions, Validators, and Post Functions** on transitions if needed:
   - *Conditions*: Restrict who can perform a transition.
   - *Validators*: Check that required fields are filled out before transitioning.
   - *Post Functions*: Automate actions after transition (e.g., reassign issue, update field).
6. Click **Publish Draft** to activate the custom workflow.
7. Associate the workflow with your project using a **Workflow Scheme**.
