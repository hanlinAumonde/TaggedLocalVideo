import { Component, inject } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { Sidebar } from './shared/components/sidebar/sidebar';
import { Header } from './shared/components/header/header';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs';
import { environment } from '../environments/environment';
import { ErrorHandlerService } from './services/errorHandler-service/error-handler-service';
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Sidebar, Header, MatIcon],
  templateUrl: './app.html'
})
export class App {
  private router = inject(Router);
  private activatedRoute = inject(ActivatedRoute);

  public errorService = inject(ErrorHandlerService);

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
          return "Video Player";
        }
        return route.snapshot.data['headerTitle'] ?? 'Loading...';
      })
    ),
    { initialValue: 'Loading...' }
  );
}