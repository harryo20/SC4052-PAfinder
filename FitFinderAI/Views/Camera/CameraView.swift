import SwiftUI
import AVFoundation

// MARK: - CameraView

struct CameraView: View {
    let onCapture: (UIImage) -> Void

    @Environment(\.dismiss) private var dismiss
    @StateObject private var controller = CameraController()
    @State private var flashOn = false
    @State private var showTips = true

    var body: some View {
        ZStack {
            // Camera preview
            CameraPreviewLayer(session: controller.session)
                .ignoresSafeArea()

            // Viewfinder overlay
            viewfinderOverlay

            // Controls
            VStack {
                topBar
                Spacer()
                if showTips {
                    tipBanner
                }
                bottomBar
            }
        }
        .onAppear {
            controller.requestPermission { granted in
                if granted { controller.start() }
            }
        }
        .onDisappear { controller.stop() }
        .onChange(of: controller.capturedImage) { _, image in
            guard let image else { return }
            onCapture(image)
            dismiss()
        }
        .preferredColorScheme(.dark)
    }

    // MARK: - Subviews

    private var viewfinderOverlay: some View {
        GeometryReader { geo in
            let w = geo.size.width * 0.75
            let h = w * 1.2
            let x = (geo.size.width  - w) / 2
            let y = (geo.size.height - h) / 2

            ZStack {
                // Dim everything outside the frame
                Color.black.opacity(0.45)
                    .mask(
                        Rectangle()
                            .overlay(
                                RoundedRectangle(cornerRadius: 20)
                                    .frame(width: w, height: h)
                                    .blendMode(.destinationOut)
                            )
                    )
                    .ignoresSafeArea()

                // Corner brackets
                RoundedRectangle(cornerRadius: 20)
                    .strokeBorder(Color.white.opacity(0.8), lineWidth: 2)
                    .frame(width: w, height: h)
                    .position(x: geo.size.width / 2, y: geo.size.height / 2)
            }
        }
    }

    private var topBar: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.title3)
                    .foregroundColor(.white)
                    .padding(12)
                    .background(.ultraThinMaterial.opacity(0.6))
                    .clipShape(Circle())
            }

            Spacer()

            Button {
                flashOn.toggle()
                controller.toggleFlash(on: flashOn)
            } label: {
                Image(systemName: flashOn ? "bolt.fill" : "bolt.slash")
                    .font(.title3)
                    .foregroundColor(flashOn ? .yellow : .white)
                    .padding(12)
                    .background(.ultraThinMaterial.opacity(0.6))
                    .clipShape(Circle())
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 60)
    }

    private var bottomBar: some View {
        VStack(spacing: 20) {
            // Shutter button
            Button {
                controller.capturePhoto()
            } label: {
                ZStack {
                    Circle()
                        .fill(.white)
                        .frame(width: 80, height: 80)
                        .shadow(color: .white.opacity(0.3), radius: 10)
                    Circle()
                        .stroke(.white, lineWidth: 4)
                        .frame(width: 92, height: 92)
                }
            }
            .disabled(controller.isCapturing)
            .scaleEffect(controller.isCapturing ? 0.9 : 1.0)
            .animation(.spring(response: 0.3), value: controller.isCapturing)

            Text("Tap to capture clothing item")
                .font(.caption)
                .foregroundColor(.white.opacity(0.8))
        }
        .padding(.bottom, 50)
    }

    private var tipBanner: some View {
        HStack(spacing: 8) {
            Image(systemName: "lightbulb.fill")
                .foregroundColor(.yellow)
                .font(.caption)
            Text("Center the clothing item in the frame")
                .font(.caption)
                .foregroundColor(.white)
            Spacer()
            Button {
                withAnimation { showTips = false }
            } label: {
                Image(systemName: "xmark")
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.6))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.ultraThinMaterial.opacity(0.7))
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .padding(.horizontal, 20)
        .padding(.bottom, 12)
    }
}

// MARK: - CameraPreviewLayer

struct CameraPreviewLayer: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> PreviewUIView {
        let view = PreviewUIView()
        view.session = session
        return view
    }

    func updateUIView(_ uiView: PreviewUIView, context: Context) {}

    class PreviewUIView: UIView {
        var session: AVCaptureSession? {
            didSet {
                guard let session else { return }
                previewLayer.session = session
            }
        }

        var previewLayer: AVCaptureVideoPreviewLayer {
            layer as! AVCaptureVideoPreviewLayer
        }

        override class var layerClass: AnyClass {
            AVCaptureVideoPreviewLayer.self
        }

        override func layoutSubviews() {
            super.layoutSubviews()
            previewLayer.videoGravity = .resizeAspectFill
            previewLayer.frame = bounds
        }
    }
}

// MARK: - CameraController

@MainActor
final class CameraController: NSObject, ObservableObject {
    @Published var capturedImage: UIImage?
    @Published var isCapturing = false

    let session = AVCaptureSession()
    private var photoOutput = AVCapturePhotoOutput()
    private var currentDevice: AVCaptureDevice?

    func requestPermission(completion: @escaping (Bool) -> Void) {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            completion(true)
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { granted in
                DispatchQueue.main.async { completion(granted) }
            }
        default:
            completion(false)
        }
    }

    func start() {
        guard !session.isRunning else { return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.setupSession()
            self?.session.startRunning()
        }
    }

    func stop() {
        guard session.isRunning else { return }
        DispatchQueue.global(qos: .background).async { [weak self] in
            self?.session.stopRunning()
        }
    }

    func capturePhoto() {
        guard !isCapturing else { return }
        isCapturing = true
        let settings = AVCapturePhotoSettings()
        settings.flashMode = currentDevice?.hasFlash == true ? settings.flashMode : .off
        photoOutput.capturePhoto(with: settings, delegate: self)
    }

    func toggleFlash(on: Bool) {
        guard let device = currentDevice, device.hasTorch else { return }
        try? device.lockForConfiguration()
        device.torchMode = on ? .on : .off
        device.unlockForConfiguration()
    }

    private func setupSession() {
        session.beginConfiguration()
        session.sessionPreset = .photo

        guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: camera) else {
            session.commitConfiguration()
            return
        }

        currentDevice = camera

        if session.canAddInput(input) { session.addInput(input) }
        if session.canAddOutput(photoOutput) { session.addOutput(photoOutput) }

        session.commitConfiguration()
    }
}

// MARK: - AVCapturePhotoCaptureDelegate

extension CameraController: AVCapturePhotoCaptureDelegate {
    nonisolated func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        Task { @MainActor in
            self.isCapturing = false
            guard error == nil,
                  let data = photo.fileDataRepresentation(),
                  let image = UIImage(data: data) else { return }
            self.capturedImage = image
        }
    }
}
