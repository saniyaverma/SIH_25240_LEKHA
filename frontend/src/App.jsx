import React, { useState } from "react";
import axios from "axios";
import { useDropzone } from "react-dropzone";

function App() {
  const [file, setFile] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [extractedText, setExtractedText] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [detectedLang, setDetectedLang] = useState("");

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      const selectedFile = acceptedFiles[0];
      setFile(selectedFile);
      setImageUrl(URL.createObjectURL(selectedFile));
      setExtractedText("");
      setTranslatedText("");
      setDetectedLang("");
    },
    accept: { "image/*": [], "application/pdf": [] },
    multiple: false,
  });

  const handleExtract = async () => {
    if (!file) return alert("Please upload a file!");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("http://127.0.0.1:5000/extract", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setExtractedText(res.data.text);
      setDetectedLang(res.data.language);
    } catch (err) {
      console.error(err);
      alert("Error extracting text");
    }
  };

  const handleTranslate = async () => {
    if (!extractedText) return alert("No text to translate!");
    try {
      const res = await axios.post("http://127.0.0.1:5000/translate", {
        text: extractedText,
      });
      setTranslatedText(res.data.translated);
    } catch (err) {
      console.error(err);
      alert("Error translating text");
    }
  };

  const handleDownload = () => {
    const element = document.createElement("a");
    const fileBlob = new Blob([translatedText], { type: "text/plain" });
    element.href = URL.createObjectURL(fileBlob);
    element.download = "translation.txt";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div
      className="d-flex justify-content-center align-items-center min-vh-100"
      style={{
        backgroundImage:
          "url('https://media.istockphoto.com/id/962839792/vector/vector-illustration-of-plain-beige-grungy-background.jpg?s=612x612&w=0&k=20&c=1uYWy5WuhiCVp2O5-3DYUaucKouuLWLcoI3Okr_aoCQ=')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
        minHeight: "100vh",
        padding: "20px",
      }}
    >
      <div
        className="shadow-lg p-5 rounded-4 w-100"
        style={{
          maxWidth: "1000px",
          background: "rgba(255, 255, 255, 0.9)",
          fontFamily: "Georgia, serif",
          border: "1px solid #d2b48c",
          boxShadow: "0 4px 12px rgba(139, 69, 19, 0.3)",
        }}
      >
        <h1 className="text-center mb-3" style={{ color: "#8B4513" }}>
          LEKHA
        </h1>
        <p
          className="text-center mb-4"
          style={{ color: "#A0522D", fontSize: "1.1rem" }}
        >
          Literary Heritage AI - bridging scripts, stories, and souls 📚🖋
        </p>

        {/* --- Dropzone --- */}
        <div
          {...getRootProps()}
          className="dropzone border border-dashed rounded-3 p-5 text-center mb-4"
          style={{
            background: "#fdf6f0",
            cursor: "pointer",
            border: "2px dashed #d2b48c",
          }}
        >
          <input {...getInputProps()} />
          {isDragActive ? (
            <p>Drop file here...</p>
          ) : (
            <p>Drag & drop image/PDF here or click to select file</p>
          )}
        </div>

        {/* --- Action Buttons --- */}
        <div className="text-center mb-4">
          <button className="btn btn-primary mx-2" onClick={handleExtract}>
            Extract Text
          </button>
          <button className="btn btn-success mx-2" onClick={handleTranslate}>
            Translate
          </button>
          {translatedText && (
            <button className="btn btn-secondary mx-2" onClick={handleDownload}>
              Download Translation
            </button>
          )}
        </div>

        {/* --- Language Detection --- */}
        {detectedLang && (
          <div className="mb-3 text-center">
            <strong>Detected Language:</strong> {detectedLang.toUpperCase()}
          </div>
        )}

        {/* --- Image + Text Sections --- */}
        <div className="row">
          {imageUrl && (
            <div className="col-md-6 mb-3">
              <img
                src={imageUrl}
                alt="uploaded"
                className="img-fluid rounded"
                style={{ border: "1px solid #d2b48c" }}
              />
            </div>
          )}

          <div className="col-md-6">
            {/* Only show Extracted Text box after extraction */}
            {extractedText && (
              <textarea
                className="form-control mb-3"
                rows={10}
                value={extractedText}
                onChange={(e) => setExtractedText(e.target.value)}
                style={{
                  fontFamily: "Georgia, serif",
                  backgroundColor: "#fffdf8",
                  borderColor: "#d2b48c",
                }}
              ></textarea>
            )}

            {/* Only show Translated Text box after translation */}
            {translatedText && (
              <textarea
                className="form-control"
                rows={10}
                value={translatedText}
                onChange={(e) => setTranslatedText(e.target.value)}
                style={{
                  fontFamily: "Georgia, serif",
                  backgroundColor: "#fffdf8",
                  borderColor: "#d2b48c",
                }}
              ></textarea>
            )}
          </div>
        </div>

        <footer className="footer text-center mt-5">
          <p style={{ color: "#8B4513" }}>
            Made with 💛 for heritage and language preservation.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
