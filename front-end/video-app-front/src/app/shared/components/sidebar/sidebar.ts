import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, MatIconModule, MatButtonModule, MatTooltipModule],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css',
})
export class Sidebar {
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
}
