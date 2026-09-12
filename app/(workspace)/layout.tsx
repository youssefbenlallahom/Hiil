import Workspace from '@/components/workspace';

// Keep the selected dossier and in-progress UI state when changing screens.
export default function WorkspaceLayout({children}:{children:React.ReactNode}) {
  return <><Workspace/>{children}</>;
}
