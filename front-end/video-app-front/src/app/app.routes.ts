import { Routes } from '@angular/router';
import { Homepage } from './pages/homepage/homepage';
import { Search } from './pages/search/search'
import { VideoPlayer } from './pages/video-player/video-player'
import { Management } from './pages/management/management'


export const routes: Routes = [
  {
    path: '',
    redirectTo: '/home',
    pathMatch: 'full',
  },
  {
    path: 'home',
    component: Homepage,
  },
  {
    path: 'search',
    component: Search,
  },
  {
    path: 'video/:id',
    component: VideoPlayer,
  },
  {
    path: 'management',
    component: Management,
  },
  {
    path: '**',
    redirectTo: '/home',
  },
];
