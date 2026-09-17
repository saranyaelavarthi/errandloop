// Ownership and participation are built from server state, never client claims.
permit(principal is Member, action == Action::"post", resource is Group)
when { principal.group == resource.id };

permit(principal is Member, action == Action::"cancel_post", resource is Post)
when { resource.owner == principal && resource.group == principal.group };

permit(principal is Member,
       action in [Action::"propose", Action::"accept", Action::"decline", Action::"cancel_loop"],
       resource is Loop)
when { resource.members.contains(principal) && resource.group == principal.group };

permit(principal is Member, action == Action::"collected", resource is Handover)
when { resource.giver == principal && resource.group == principal.group };

permit(principal is Member, action == Action::"received", resource is Handover)
when { resource.receiver == principal && resource.group == principal.group };
