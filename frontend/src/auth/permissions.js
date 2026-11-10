export function canAccess(user, roles) {
  return Boolean(user && (!roles || roles.includes(user.role) || (roles.includes('ADMIN') && user.capacidades?.gestionar_pedidos) || (roles.includes('VENDEDOR') && user.capacidades?.gestionar_productos)))
}
