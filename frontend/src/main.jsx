import { render } from 'preact';
import { App } from './app';
import './theme/tokens.css';
import './theme/light.css';
import './theme/dark.css';
import './theme/global.css';

render(<App />, document.getElementById('app'));
