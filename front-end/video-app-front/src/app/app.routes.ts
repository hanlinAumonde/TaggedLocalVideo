import { Routes } from '@angular/router';
import { Homepage } from './pages/homepage/homepage';
import { Search } from './pages/search/search'
import { VideoPlayer } from './pages/video-player/video-player'
import { Management } from './pages/management/management'
import { VideoMetaDataResolver } from './route-resolver/video-player.resolver';


export const routes: Routes = [
  {
    path: '',
    redirectTo: '/home',
    pathMatch: 'full',
  },
  {
    path: 'home',
    title: 'Home Page - Tagged Local Video App',
    component: Homepage,
    data: { headerTitle: 'HomePage' }
  },
  {
    path: 'search',
    title: 'Search videos - Tagged Local Video App',
    component: Search,
    data: { headerTitle: 'Search' }
  },
  {
    path: 'video/:id',
    component: VideoPlayer,
    title: 'Video Player - Tagged Local Video App',
    resolve: {
      video: VideoMetaDataResolver
    }
  },
  {
    path: 'management',
    component: Management,
    title: 'Management - Tagged Local Video App',
    data: { headerTitle: 'Management' } 
  },
  {
    path: '**',
    redirectTo: '/home',
  },
];
