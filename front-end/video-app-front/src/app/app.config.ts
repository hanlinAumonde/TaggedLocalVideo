import { ApplicationConfig, inject, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { HTTP_INTERCEPTORS, provideHttpClient, withFetch, withInterceptorsFromDi } from '@angular/common/http';
import { provideApollo } from 'apollo-angular';
import { environment } from '../environments/environment';
import { routes } from './app.routes';
import { HttpLink } from 'apollo-angular/http';
import { InMemoryCache } from '@apollo/client';
import { ImageRequestInterceptor } from './shared/interceptor/ImageRequest.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(),
    provideHttpClient(
      withFetch(),
      withInterceptorsFromDi()
    ),
    {
      provide: HTTP_INTERCEPTORS,
      useClass: ImageRequestInterceptor,
      multi: true
    },
    provideApollo(() => {
      const httpLink = inject(HttpLink)
      return {
        link: httpLink.create({ uri: environment.backend_api + "/graphql" }),
        cache: new InMemoryCache({
          typePolicies: {
            Query: {
              fields: {
                // Search result pagination merging strategy
                SearchVideos: {
                  keyArgs: ['input', ['titleKeyword', 'author', 'tags', 'sortBy']],
                  merge(existing, incoming) {
                    return incoming; // Replace each time, do not merge paginated results
                  },
                },
              },
            },
          },
        }),
        defaultOptions: {
          watchQuery: {
            fetchPolicy: 'cache-and-network', 
            errorPolicy: 'all',
          },
          query: {
            fetchPolicy: 'network-only',
            errorPolicy: 'all',
          },
          mutate: {
            errorPolicy: 'all',
          },
        },
      };
    }),
  ],
};
