import { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="layout">
      <header className="header">
        <div className="logo">Tender Intelligence</div>
        <div className="user-profile">User</div>
      </header>
      
      <div className="main-container">
        <aside className="sidebar">
          <nav>
            <NavLink to="/" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Dashboard</NavLink>
            <NavLink to="/opportunities" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Opportunities</NavLink>
            <NavLink to="/sources" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Sources</NavLink>
            <NavLink to="/content" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>Content</NavLink>
            <NavLink to="/matches" className="nav-link disabled" onClick={e => e.preventDefault()}>Matches</NavLink>
            <NavLink to="/notifications" className="nav-link disabled" onClick={e => e.preventDefault()}>Notifications</NavLink>
            <NavLink to="/settings" className="nav-link disabled" onClick={e => e.preventDefault()}>Settings</NavLink>
          </nav>
        </aside>
        
        <main className="content">
          {children}
        </main>
      </div>
    </div>
  );
}

