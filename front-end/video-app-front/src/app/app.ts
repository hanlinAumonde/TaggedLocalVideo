import { Component, effect, inject } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { Sidebar } from './shared/components/sidebar/sidebar';
import { Header } from './shared/components/header/header';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map, tap } from 'rxjs';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Sidebar, Header],
  templateUrl: './app.html'
})
export class App {
  private router = inject(Router);
  private activatedRoute = inject(ActivatedRoute);

  rootMainContainerId = environment.rootMainContainerId;

  headerTitle = toSignal(
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd),
      map(() => {
        let route = this.activatedRoute;
        while (route.firstChild) {
          route = route.firstChild;
        }
        if(route.snapshot.data['video']){
          const videoTitle = route.snapshot.data['video']?.data?.name;
          return "Video Player" + (videoTitle ? ` - ${videoTitle}` : '');
        }
        return route.snapshot.data['headerTitle'] ?? 'Loading...';
      })
    ),
    { initialValue: 'Loading...' }
  );
}
