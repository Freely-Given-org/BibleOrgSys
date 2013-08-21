\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{Bible}[2013/08/21 custom Bible class]
\LoadClass{book}
\RequirePackage{lettrine} % Finds lettrine.sty


% \RequirePackage{titlesec}

% \titleformat{\section}
%   {\Large\scshape\raggedright}
%   {}{0em}
%   {}
%   [\titlerule]
%
%   \titleformat{\subsection}
%   {\large\scshape\raggedright}
%   {}{0em}
%   {}
%
%   \newcommand{\datedsection}[2]{
%   \section[#1]{#1 \hfill #2}
% }


\newcommand{\BibleBook}[1]{
  \newpage
  \centerline{\Huge{#1}}
}

\newcommand{\BibleText}[0]{
  \part{}
}

\newcommand{\BibleTextSection}[1]{
  \section{#1}
}

\newcommand{\BibleSectionReference}[1]{
  \centerline{#1}
}

\newcommand{\chapterNumber}[1]{
    \lettrine[lines=3,slope=-4pt,nindent=-4pt]{#1}{~}
}
% {\em #1}

\newcommand{\verseNumber}[1]{
    \textsuperscript{#1~}
}

\newcommand{\BibleParagraphStyleP}[0]{
    \par
}
\newcommand{\BibleParagraphStylePI}[0]{
    \par
}
\newcommand{\BibleParagraphStyleQ}[0]{
    \par
}
\newcommand{\BibleParagraphStyleQQ}[0]{
    \par
}
\newcommand{\BibleParagraphStyleQQQ}[0]{
    \par
}
\newcommand{\BibleParagraphStyleQQQQQ}[0]{
    \par
}

% \newcommand{\contact}[5]{
%     #1 {\large\textperiodcentered} #2 {\large\textperiodcentered} #3
%     {\Large} #4 \ {\Large} #5
% }
%
% \newcommand{\longcontact}[5]{
%     \center{#1 \hfill {\large\textperiodcentered} \hfill #2 \hfill {\large\textperiodcentered} \hfill #3}
%     \center{ {\Large} #4 \hfill {\Large} #5}
% }
%
% \newcommand{\workitems}[3]{
%     \begin{itemize}
%     \item #1
%     \item #2
%     \item #3
%     \end{itemize}
% }