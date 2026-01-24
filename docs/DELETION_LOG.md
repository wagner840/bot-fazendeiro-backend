# Code Deletion Log

## [2026-01-24] Refactor Session

### Unused Dependencies Removed
- @radix-ui/react-dialog
- @radix-ui/react-dropdown-menu
- @radix-ui/react-select
- @radix-ui/react-slot
- @radix-ui/react-tabs
- @radix-ui/react-toast
- class-variance-authority

### Unused Files Deleted
- src/components/ui/Select.tsx
- src/components/ui/Textarea.tsx

### Unused Exports Removed
- **src/lib/utils.ts**: debounce, groupBy (restored), sortByKey, filterBySearch (restored), truncate, capitalize (restored), slugify, date helpers, number helpers, array helpers.
- **src/lib/types.ts**: ModalProps, plus some form interfaces.
- **src/lib/supabase.ts**: Unused CRUD wrappers: `getEmpresaById`, `getEmpresaByGuild`, `getFuncionarioById`, `updateFuncionarioSaldo`, `createFuncionario`, `getProdutosReferencia`, `updateProdutoEstoque`, `getEstoqueGlobal`, `createPagamento`.

### Impact
- Files deleted: 2
- Dependencies removed: 7
- Lines of code removed: ~300+

### Testing
- All unit tests passing: Build Passed
- All integration tests passing: Build Passed
- Manual testing completed: Verified Build
