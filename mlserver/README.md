# 🍽️ 음식 질량 측정 시스템 - 프론트엔드 연동 가이드

## 📋 개요
이 문서는 음식 질량 측정 시스템의 프론트엔드 연동을 위한 API 및 WebSocket 사용법을 설명합니다.

---

## 🔗 API 엔드포인트

### 1. 이미지 업로드 API
**URL**: `POST /mlserver/api/upload/`  
**Content-Type**: `multipart/form-data`

#### 요청 예시 (JavaScript)
```javascript
async function uploadImage(file) {
    const formData = new FormData();
    formData.append('image', file);
    
    const response = await fetch('/mlserver/api/upload/', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
}

// 사용 예시
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];
const result = await uploadImage(file);
const taskId = result.data.task_id;
```

#### 성공 응답 (200 OK)
```json
{
    "success": true,
    "data": {
        "task_id": "d80265f0-8d5c-4fdf-9718-0f0d24fa98e0",
        "message": "이미지 업로드가 완료되었습니다.",
        "filename": "test.jpg"
    }
}
```

#### 실패 응답 (400/500)
```json
{
    "success": false,
    "error": "이미지 파일을 업로드할 수 없습니다."
}
```

---

## 🌐 WebSocket 연결

### WebSocket URL
```
ws://localhost:8000/ws/task/{task_id}/
```

### 연결 및 메시지 처리 (JavaScript)
```javascript
class FoodEstimationWebSocket {
    constructor(taskId) {
        this.taskId = taskId;
        this.ws = null;
        this.onProgress = null;
        this.onComplete = null;
        this.onError = null;
    }
    
    connect() {
        const wsUrl = `ws://localhost:8000/ws/task/${this.taskId}/`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket 연결됨');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket 연결 해제됨');
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket 오류:', error);
            if (this.onError) this.onError(error);
        };
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'task.update':
                // 진행률 업데이트
                if (this.onProgress) {
                    this.onProgress(data.data);
                }
                break;
                
            case 'task.completed':
                // 작업 완료
                if (this.onComplete) {
                    this.onComplete(data.data.result);
                }
                this.ws.close();
                break;
                
            case 'task.failed':
                // 작업 실패
                if (this.onError) {
                    this.onError(data.data.error);
                }
                this.ws.close();
                break;
        }
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// 사용 예시
const ws = new FoodEstimationWebSocket(taskId);

ws.onProgress = (data) => {
    console.log(`진행률: ${data.progress * 100}% - ${data.message}`);
    // UI 업데이트: 진행률 바, 메시지 등
};

ws.onComplete = (result) => {
    console.log('분석 완료:', result);
    // 결과 표시: 음식명, 질량, 신뢰도 등
};

ws.onError = (error) => {
    console.error('오류 발생:', error);
    // 에러 메시지 표시
};

ws.connect();
```

---

## 📊 메시지 형식

### 1. 진행률 업데이트 (`task.update`)
```json
{
    "type": "task.update",
    "task_id": "d80265f0-8d5c-4fdf-9718-0f0d24fa98e0",
    "data": {
        "status": "processing",
        "progress": 0.6,
        "message": "LLM 분석 중..."
    }
}
```

### 2. 작업 완료 (`task.completed`)
```json
{
    "type": "task.completed",
    "task_id": "d80265f0-8d5c-4fdf-9718-0f0d24fa98e0",
    "data": {
        "status": "completed",
        "progress": 1.0,
        "result": {
            "filename": "test.jpg",
            "detected_objects": {
                "food": 2,
                "reference_objects": 1
            },
            "mass_estimation": {
                "foods": [
                    {
                        "food_name": "김치찌개",
                        "estimated_mass_g": 320.5,
                        "confidence": 0.92,
                        "verification_method": "multimodal_verification",
                        "reasoning": "이미지에서 김치찌개가 명확히 보이며..."
                    }
                ],
                "total_mass_g": 320.5,
                "food_count": 1
            }
        },
        "message": "음식 분석이 완료되었습니다."
    }
}
```

### 3. 작업 실패 (`task.failed`)
```json
{
    "type": "task.failed",
    "task_id": "d80265f0-8d5c-4fdf-9718-0f0d24fa98e0",
    "data": {
        "status": "failed",
        "error": "이미지 처리 중 오류가 발생했습니다.",
        "message": "ML 서버 오류: 서버 내부 오류가 발생했습니다."
    }
}
```

---

## 🚀 완전한 사용 예시

```javascript
class FoodCalorieApp {
    constructor() {
        this.currentTaskId = null;
        this.currentWebSocket = null;
    }
    
    async startEstimation(file) {
        try {
            // 1. 이미지 업로드
            const uploadResult = await this.uploadImage(file);
            this.currentTaskId = uploadResult.data.task_id;
            
            // 2. WebSocket 연결
            this.connectWebSocket();
            
            return this.currentTaskId;
        } catch (error) {
            console.error('작업 시작 실패:', error);
            throw error;
        }
    }
    
    async uploadImage(file) {
        const formData = new FormData();
        formData.append('image', file);
        
        const response = await fetch('/mlserver/api/upload/', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`업로드 실패: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    connectWebSocket() {
        if (!this.currentTaskId) {
            throw new Error('작업 ID가 없습니다.');
        }
        
        this.currentWebSocket = new FoodEstimationWebSocket(this.currentTaskId);
        
        this.currentWebSocket.onProgress = (data) => {
            this.updateProgress(data);
        };
        
        this.currentWebSocket.onComplete = (result) => {
            this.showResult(result);
        };
        
        this.currentWebSocket.onError = (error) => {
            this.showError(error);
        };
        
        this.currentWebSocket.connect();
    }
    
    updateProgress(data) {
        // 진행률 UI 업데이트
        const progressPercent = data.progress * 100;
        console.log(`진행률: ${progressPercent}% - ${data.message}`);
        
        // 예시: 진행률 바 업데이트
        // document.getElementById('progress-bar').style.width = `${progressPercent}%`;
        // document.getElementById('progress-text').textContent = data.message;
    }
    
    showResult(result) {
        console.log('분석 결과:', result);
        
        // 예시: 결과 표시
        const foods = result.mass_estimation.foods;
        const totalMass = result.mass_estimation.total_mass_g;
        
        console.log(`총 질량: ${totalMass}g`);
        foods.forEach(food => {
            console.log(`${food.food_name}: ${food.estimated_mass_g}g (신뢰도: ${food.confidence})`);
        });
    }
    
    showError(error) {
        console.error('오류:', error);
        // 예시: 에러 메시지 표시
        // alert(`오류가 발생했습니다: ${error}`);
    }
    
    disconnect() {
        if (this.currentWebSocket) {
            this.currentWebSocket.disconnect();
            this.currentWebSocket = null;
        }
    }
}

// 사용 예시
const app = new FoodCalorieApp();

// 파일 업로드 시
const fileInput = document.getElementById('fileInput');
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        try {
            await app.startEstimation(file);
        } catch (error) {
            console.error('작업 시작 실패:', error);
        }
    }
});
```

---

## 📝 주의사항

### 1. 파일 제한
- **지원 형식**: JPG, PNG, JPEG
- **최대 크기**: 10MB
- **최대 해상도**: 1920px

### 2. WebSocket 연결
- **자동 재연결**: 구현하지 않음 (필요시 별도 구현)
- **연결 해제**: 작업 완료/실패 시 자동 해제
- **에러 처리**: 연결 실패 시 적절한 에러 메시지 표시

### 3. 에러 처리
- **네트워크 오류**: 재시도 로직 구현 권장
- **서버 오류**: 사용자에게 명확한 메시지 표시
- **타임아웃**: 30초 이상 응답 없으면 오류 처리

---

## 🔧 추가 기능

### 1. 진행률 바 애니메이션
```javascript
function updateProgressBar(progress) {
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = `${progress * 100}%`;
    progressBar.style.transition = 'width 0.3s ease';
}
```

### 2. 결과 카드 표시
```javascript
function displayResultCard(result) {
    const foods = result.mass_estimation.foods;
    const totalMass = result.mass_estimation.total_mass_g;
    
    const resultHTML = `
        <div class="result-card">
            <h3>분석 결과</h3>
            <p>총 질량: ${totalMass}g</p>
            <ul>
                ${foods.map(food => `
                    <li>${food.food_name}: ${food.estimated_mass_g}g (${(food.confidence * 100).toFixed(1)}%)</li>
                `).join('')}
            </ul>
        </div>
    `;
    
    document.getElementById('result-container').innerHTML = resultHTML;
}
```

---

## 📞 지원

문제가 발생하거나 추가 기능이 필요한 경우:
1. Django 서버 로그 확인
2. Celery 워커 로그 확인
3. ML 서버 로그 확인
4. 브라우저 개발자 도구 Console 확인 