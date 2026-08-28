import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/home/home.component').then(m => m.HomeComponent),
    title: 'AgroIA Casanare — Mercado campesino',
  },
  {
    path: 'catalogo',
    loadComponent: () => import('./pages/catalogo/catalogo.component').then(m => m.CatalogoComponent),
    title: 'Catálogo de ofertas — AgroIA Casanare',
  },
  {
    path: 'buscar',
    loadComponent: () => import('./pages/buscar/buscar.component').then(m => m.BuscarComponent),
    title: 'Buscar con IA — AgroIA Casanare',
  },
  {
    path: 'panel',
    loadComponent: () => import('./pages/panel/panel.component').then(m => m.PanelComponent),
    title: 'Panel del mercado — AgroIA Casanare',
  },
  {
    // Sin enlace en el menú a propósito: se llega escribiendo /admin.
    path: 'admin',
    loadComponent: () => import('./pages/admin/admin.component').then(m => m.AdminComponent),
    title: 'Administración — AgroIA Casanare',
  },
  {
    path: 'publicar',
    loadComponent: () => import('./pages/publicar/publicar.component').then(m => m.PublicarComponent),
    title: 'Publicar una oferta — AgroIA Casanare',
  },
  { path: '**', redirectTo: '' },
];
