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
            <NavLink to="/explore" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                Explore Tenders
                <span style={{ fontSize: '0.65rem', background: '#3b82f6', color: '#fff', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>AI</span>
              </span>
            </NavLink>
            <NavLink to="/scraped-tenders" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                Tender Scraper
                <span style={{ fontSize: '0.65rem', background: '#10b981', color: '#fff', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>LIVE DB</span>
              </span>
            </NavLink>
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

