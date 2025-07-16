from django.shortcuts import render

# Create your views here.

def test_websocket(request):
    """웹소켓 테스트 페이지"""
    return render(request, 'mlserver/test_websocket.html')
