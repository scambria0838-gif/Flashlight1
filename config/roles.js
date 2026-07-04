// Role & permission model for Majority AI.
//
// Roles are additive permission sets. The "overseer" role is intentionally NOT
// removable at runtime: the whole point of the council is that a reviewer signs
// off on any action that touches the host system. There is no "disable
// oversight" switch by design.

export const PERMISSIONS = {
  VIEW: 'view',              // read the dashboard, watch council debates
  DISPATCH: 'dispatch',      // send prompts to the council
  MANAGE_MODELS: 'models',   // toggle which models participate
  APPROVE_ACTIONS: 'approve' // sign off on any host-system action (overseer only)
};

export const ROLES = {
  viewer: {
    title: 'Viewer',
    permissions: [PERMISSIONS.VIEW]
  },
  operator: {
    title: 'Operator',
    permissions: [PERMISSIONS.VIEW, PERMISSIONS.DISPATCH, PERMISSIONS.MANAGE_MODELS]
  },
  // The Safeguard Overseer: full access, and the only role that can approve
  // host-system actions. This role's approval requirement cannot be toggled off.
  overseer: {
    title: 'Safeguard Overseer',
    permissions: [
      PERMISSIONS.VIEW,
      PERMISSIONS.DISPATCH,
      PERMISSIONS.MANAGE_MODELS,
      PERMISSIONS.APPROVE_ACTIONS
    ]
  }
};

export function can(role, permission) {
  const def = ROLES[role];
  return Boolean(def && def.permissions.includes(permission));
}
