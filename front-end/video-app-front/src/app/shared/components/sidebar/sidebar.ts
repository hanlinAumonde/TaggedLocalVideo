import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { PageStateService } from '../../../services/Page-state-service/page-state';
import { environment } from '../../../../environments/environment.development';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, MatIconModule, MatButtonModule, MatTooltipModule],
  templateUrl: './sidebar.html'
})
export class Sidebar {
  private stateService = inject(PageStateService);

  isExpanded = signal(false);

  navItems: NavItem[] = [
    {
      path: '/home',
      label: 'Dashboard',
      icon: 'person',
    },
    {
      path: '/search',
      label: 'Search',
      icon: 'search',
    },
    {
      path: '/management',
      label: 'Management',
      icon: 'build',
    },
  ];

  toggleSidebar() {
    this.isExpanded.update((value) => !value);
  }

  onNavItemClick() {
    this.stateService.clearAllStates(false);
  }

  private getParentScrollContainer(): HTMLElement | null {
      return document.getElementById(environment.rootMainContainerId);
    }
  
  scrollTo(position: number) {
    const mainContainer = this.getParentScrollContainer();
    if (mainContainer) {
      mainContainer.scrollTo({ top: position, behavior: 'smooth' });
    }
  }
}
