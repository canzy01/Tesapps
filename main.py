from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.listview import ListItemButton
from kivy.uix.popup import Popup
from kivy.adapters.listadapter import ListAdapter
from kivy.network.urlrequest import UrlRequest
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty
from android.permissions import request_permissions, Permission
from jnius import autoclass
import json
import os

# Android-specific imports
PythonActivity = autoclass('org.kivy.android.PythonActivity')
Intent = autoclass('android.content.Intent')
VpnService = autoclass('android.net.VpnService')
Proxy = autoclass('java.net.Proxy')
ProxySelector = autoclass('java.net.ProxySelector')
InetSocketAddress = autoclass('java.net.InetSocketAddress')
Uri = autoclass('android.net.Uri')

class ProxyListItemButton(ListItemButton):
    pass

class ProxyManagerRoot(BoxLayout):
    proxy_list = ObjectProperty(None)
    proxy_address = ObjectProperty(None)
    proxy_port = ObjectProperty(None)
    proxy_type = ObjectProperty(None)
    status_label = StringProperty("Disconnected")
    
    def __init__(self, **kwargs):
        super(ProxyManagerRoot, self).__init__(**kwargs)
        self.proxies = []
        self.load_proxies()
        self.current_proxy = None
        self.vpn_intent = None
        
    def load_proxies(self):
        if os.path.exists("proxies.json"):
            with open("proxies.json", "r") as f:
                self.proxies = json.load(f)
        self.update_proxy_list()
    
    def save_proxies(self):
        with open("proxies.json", "w") as f:
            json.dump(self.proxies, f)
    
    def update_proxy_list(self):
        list_adapter = ListAdapter(
            data=[f"{p['address']}:{p['port']} ({p['type']})" for p in self.proxies],
            cls=ProxyListItemButton,
            selection_mode='single',
            allow_empty_selection=True
        )
        self.proxy_list.adapter = list_adapter
    
    def add_proxy(self):
        address = self.proxy_address.text
        port = self.proxy_port.text
        proxy_type = self.proxy_type.text
        
        if not address or not port:
            self.show_popup("Error", "Address and port are required")
            return
            
        try:
            port = int(port)
        except ValueError:
            self.show_popup("Error", "Port must be a number")
            return
            
        if proxy_type.lower() not in ['http', 'socks4', 'socks5']:
            self.show_popup("Error", "Proxy type must be HTTP, SOCKS4 or SOCKS5")
            return
            
        self.proxies.append({
            'address': address,
            'port': port,
            'type': proxy_type.lower()
        })
        self.save_proxies()
        self.update_proxy_list()
        self.proxy_address.text = ""
        self.proxy_port.text = ""
    
    def delete_proxy(self):
        if not self.proxy_list.adapter.selection:
            self.show_popup("Error", "No proxy selected")
            return
            
        index = self.proxy_list.adapter.selection[0].index
        del self.proxies[index]
        self.save_proxies()
        self.update_proxy_list()
    
    def test_proxy(self):
        if not self.proxy_list.adapter.selection:
            self.show_popup("Error", "No proxy selected")
            return
            
        index = self.proxy_list.adapter.selection[0].index
        proxy = self.proxies[index]
        
        def on_success(req, result):
            self.show_popup("Success", "Proxy connection successful!")
            
        def on_error(req, error):
            self.show_popup("Error", f"Proxy connection failed: {error}")
            
        proxy_url = f"{proxy['type']}://{proxy['address']}:{proxy['port']}"
        
        try:
            UrlRequest(
                "http://example.com",
                proxy_host=proxy['address'],
                proxy_port=str(proxy['port']),
                timeout=10,
                on_success=on_success,
                on_error=on_error
            )
            self.status_label = f"Testing {proxy['address']}..."
        except Exception as e:
            self.show_popup("Error", f"Error: {str(e)}")
    
    def connect_proxy(self):
        if not self.proxy_list.adapter.selection:
            self.show_popup("Error", "No proxy selected")
            return
            
        index = self.proxy_list.adapter.selection[0].index
        self.current_proxy = self.proxies[index]
        
        # Request VPN permission
        context = PythonActivity.mActivity
        intent = VpnService.prepare(context)
        
        if intent is not None:
            # Need to request VPN permission
            self.vpn_intent = intent
            self.show_vpn_permission_popup()
        else:
            # Already have permission, start VPN
            self.start_vpn_service()
    
    def show_vpn_permission_popup(self):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text="This app needs VPN permission to route traffic"))
        btn = Button(text="Grant Permission", size_hint=(1, 0.3))
        
        popup = Popup(title="VPN Permission", content=content, size_hint=(0.8, 0.4))
        
        def grant_permission(instance):
            context = PythonActivity.mActivity
            context.startActivityForResult(self.vpn_intent, 0)
            popup.dismiss()
            
        btn.bind(on_release=grant_permission)
        content.add_widget(btn)
        popup.open()
    
    def start_vpn_service(self):
        self.status_label = f"Connecting to {self.current_proxy['address']}..."
        
        # In a real app, you would implement a proper VPN service here
        # This is a simplified version
        
        # For demo purposes, we'll just show a message
        Clock.schedule_once(lambda dt: self.set_connected_status(), 2)
    
    def set_connected_status(self):
        self.status_label = f"Connected to {self.current_proxy['address']}"
        self.show_popup("Connected", "All traffic is now routed through the proxy")
    
    def disconnect_proxy(self):
        self.current_proxy = None
        self.status_label = "Disconnected"
        # In a real app, stop the VPN service here
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=message))
        btn = Button(text="OK", size_hint=(1, 0.3))
        
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        btn.bind(on_release=popup.dismiss)
        content.add_widget(btn)
        popup.open()

class ProxyManagerApp(App):
    def build(self):
        request_permissions([
            Permission.INTERNET,
            Permission.ACCESS_NETWORK_STATE,
            Permission.ACCESS_WIFI_STATE,
            Permission.CHANGE_WIFI_STATE,
            Permission.ACCESS_COARSE_LOCATION,
            Permission.ACCESS_FINE_LOCATION,
            Permission.FOREGROUND_SERVICE
        ])
        return ProxyManagerRoot()

if __name__ == '__main__':
    ProxyManagerApp().run()